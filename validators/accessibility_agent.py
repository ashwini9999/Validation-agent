# agents/accessibility_agent.py
import asyncio
import os
import re
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from playwright.async_api import async_playwright, Page, ElementHandle
from logging_config import (
    log_agent_start, log_agent_thinking, log_agent_complete,
    log_agent_error, log_playwright_action
)
from utility.agent_helper import AXE_LOCAL_PATHS, _ensure_dir

LOOP_URL_HOST = "local.loop.microsoft.com"

# # ---------------- FS helpers ----------------
# def _ensure_dir(path: str):
#     os.makedirs(path, exist_ok=True)

# def _ts() -> str:
#     return datetime.now().strftime("%Y%m%d-%H%M%S")

# # ---------------- axe-core helpers ----------------
# AXE_LOCAL_PATHS = [
#     "third_party/axe.min.js",        # preferred vendored path
#     "axe.min.js"                     # fallback if you drop it in project root
# ]

async def _inject_axe_by_source(page: Page) -> None:
    """
    Robust against Trusted Types: inject axe by SOURCE (inline), not URL.
    Requires axe.min.js to be present locally.
    """
    last_err = None
    for p in AXE_LOCAL_PATHS:
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    src = f.read()
                await page.add_script_tag(content=src)  # inline content injection
                log_playwright_action(f"♻️ Injected axe-core from local file: {p}")
                return
        except Exception as e:
            last_err = e
    raise RuntimeError(
        f"axe.min.js not found in {AXE_LOCAL_PATHS}. "
        f"Add a vendored copy (e.g., `npm i axe-core` then copy `node_modules/axe-core/axe.min.js`). "
        f"Last error: {last_err}"
    )

async def _run_axe(page: Page) -> Dict[str, Any]:
    await _inject_axe_by_source(page)
    results = await page.evaluate(
        """async () => await axe.run(document, { runOnly: { type: "tag", values: ["wcag2a","wcag2aa"] } })"""
    )
    return results

def _write_axe_reports(base_name: str, axe: Dict[str, Any]) -> Dict[str, str]:
    _ensure_dir("artifacts")
    json_path = os.path.join("artifacts", f"{base_name}.json")
    html_path = os.path.join("artifacts", f"{base_name}.html")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(axe, f, ensure_ascii=False, indent=2)

    violations = axe.get("violations", []) if isinstance(axe, dict) else []
    passes = axe.get("passes", []) if isinstance(axe, dict) else []
    incomplete = axe.get("incomplete", []) if isinstance(axe, dict) else []
    url = (axe.get("url") or "") if isinstance(axe, dict) else ""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _rows(items):
        out = []
        for v in items:
            vid = v.get("id", "")
            impact = v.get("impact", "")
            desc = v.get("description", "")
            nodes = v.get("nodes", [])
            out.append(f"<tr><td>{vid}</td><td>{impact}</td><td>{len(nodes)}</td><td>{desc}</td></tr>")
        return "\n".join(out)

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"/><title>axe report — {base_name}</title>
<style>
body{{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;margin:24px}}
h1,h2{{margin:0 0 8px}} .muted{{color:#666}} table{{border-collapse:collapse;width:100%;margin:12px 0}}
th,td{{border:1px solid #ddd;padding:8px;font-size:14px}} th{{background:#f7f7f7;text-align:left}}
.pill{{display:inline-block;padding:2px 8px;border-radius:999px;background:#eee;font-size:12px;margin-left:8px}}
.warn{{background:#fde68a}} .ok{{background:#86efac}} .meh{{background:#e5e7eb}}
</style></head><body>
<h1>axe-core report</h1>
<div class="muted">Generated: {ts}</div>
<div>Target URL: <code>{url}</code></div>
<h2>Summary</h2>
<div>Violations <span class="pill warn">{len(violations)}</span>
Passes <span class="pill ok">{len(passes)}</span>
Incomplete <span class="pill meh">{len(incomplete)}</span></div>
<h2>Violations ({len(violations)})</h2>
<table><thead><tr><th>Rule</th><th>Impact</th><th>Nodes</th><th>Description</th></tr></thead>
<tbody>{_rows(violations)}</tbody></table>
<h2>Passes ({len(passes)})</h2>
<table><thead><tr><th>Rule</th><th>Impact</th><th>Nodes</th><th>Description</th></tr></thead>
<tbody>{_rows(passes)}</tbody></table>
<h2>Incomplete ({len(incomplete)})</h2>
<table><thead><tr><th>Rule</th><th>Impact</th><th>Nodes</th><th>Description</th></tr></thead>
<tbody>{_rows(incomplete)}</tbody></table>
</body></html>"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    return {"json": json_path, "html": html_path}

# ---------------- MS login helpers ----------------
async def click_sign_in_and_capture_ms_page(main_page: Page, wait_ms: int = 15000) -> Optional[Page]:
    log_playwright_action("🔎 Locating 'Sign In' trigger on app...")
    clicked = False
    try:
        async with main_page.context.expect_page() as new_page_info:
            try:
                await main_page.get_by_role("button", name=re.compile(r"sign in", re.I)).click()
                clicked = True
            except Exception:
                pass
            if not clicked:
                try:
                    await main_page.get_by_role("link", name=re.compile(r"sign in", re.I)).click()
                    clicked = True
                except Exception:
                    pass
            if not clicked:
                locator = main_page.locator(
                    "button:has-text('Sign in'), button:has-text('Sign In'), a:has-text('Sign in'), a:has-text('Sign In')"
                )
                if await locator.count():
                    await locator.first.click()
                    clicked = True
        if clicked:
            ms_page = await new_page_info.value
            log_playwright_action("🌐 Detected Microsoft login page (popup/tab) via expect_page()")
            return ms_page
    except Exception as e:
        log_playwright_action(f"⚠️ expect_page() did not catch popup/tab: {e}")

    log_playwright_action("🔁 Scanning all pages for Microsoft login...")
    end_time = asyncio.get_event_loop().time() + (wait_ms / 1000)
    while asyncio.get_event_loop().time() < end_time:
        for p in main_page.context.pages:
            try:
                if "login.microsoftonline.com" in (p.url or ""):
                    log_playwright_action(f"✅ Found Microsoft login page by scan: {p.url}")
                    return p
            except Exception:
                pass
        await asyncio.sleep(0.25)

    log_playwright_action("❌ Could not find Microsoft login page after clicking Sign In")
    return None

async def ms_login(ms_page: Page, username: str, password: str):
    log_playwright_action("🔑 Automating Microsoft login in popup/tab")
    await ms_page.wait_for_selector("#i0116", state="visible")
    await ms_page.fill("#i0116", username)
    log_playwright_action("📧 Filled username")
    await ms_page.keyboard.press("Enter")

    await ms_page.wait_for_selector('[name="passwd"]', state="visible")
    await ms_page.fill('[name="passwd"]', password)
    log_playwright_action("🔒 Filled password")

    try:
        await ms_page.wait_for_selector('input[value="Sign in"], #idSIButton9', state="visible", timeout=15000)
        if await ms_page.locator('input[value="Sign in"]').is_visible():
            await ms_page.click('input[value="Sign in"]')
        else:
            await ms_page.click('#idSIButton9')
        log_playwright_action("✅ Clicked Sign in")
    except Exception:
        await ms_page.keyboard.press("Enter")
    try:
        await ms_page.wait_for_selector('[aria-describedby="KmsiDescription"][value="Yes"], #idSIButton9, #idBtn_Back', timeout=10000)
        if await ms_page.locator('[aria-describedby="KmsiDescription"][value="Yes"]').is_visible():
            await ms_page.click('[aria-describedby="KmsiDescription"][value="Yes"]')
            log_playwright_action("🟢 KMSI: clicked explicit 'Yes'")
        elif await ms_page.locator('#idSIButton9').is_visible():
            await ms_page.click('#idSIButton9')
            log_playwright_action("🟢 KMSI: clicked #idSIButton9 (Yes)")
    except Exception:
        log_playwright_action("ℹ️ No/Skipped KMSI")

# ---------------- page ready helpers ----------------
async def finalize_auth_after_popup(ms_page: Page, main_page: Page, website: str, timeout_seconds: int = 180) -> bool:
    log_playwright_action("⏳ Finalizing auth…")
    end_time = asyncio.get_event_loop().time() + timeout_seconds
    while asyncio.get_event_loop().time() < end_time:
        try:
            if ms_page.is_closed():
                try:
                    await main_page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                if await is_loop_ready(main_page, website):
                    return True
            else:
                if LOOP_URL_HOST in (ms_page.url or "") or website.rstrip("/") in (ms_page.url or ""):
                    try:
                        await ms_page.close()
                    except Exception:
                        pass
                    if await is_loop_ready(main_page, website):
                        return True
            if await is_loop_ready(main_page, website):
                return True
        except Exception:
            pass
        await asyncio.sleep(1.0)
    log_agent_error("A11yExec", f"Timed out finalizing auth after {timeout_seconds}s")
    return False

async def is_loop_ready(page: Page, website: str) -> bool:
    try:
        url = page.url or ""
        if LOOP_URL_HOST in url or website.rstrip("/") in url:
            try:
                h1 = page.locator("h1")
                if await h1.count():
                    texts = [t.lower() for t in await h1.all_inner_texts()]
                    if any("loop" in (t or "") for t in texts):
                        log_playwright_action(f"✅ Loop H1 detected at: {url}")
                        return True
            except Exception:
                pass
            log_playwright_action(f"✅ Loop host detected at: {url}")
            return True
    except Exception:
        pass
    return False

# ---------------- target lookup: tablist below the Search button ----------------
async def _find_tablist_below_search(page: Page, max_wait_s: float = 3.0, poll_interval: float = 0.25) -> Optional[ElementHandle]:
    """
    Robust heuristic to find tablist below the Search button.
    Retries for up to `max_wait_s` seconds in case the button or tablist is rendered asynchronously.
    """
    end_time = asyncio.get_event_loop().time() + max_wait_s

    # helper to try one pass of the logic
    async def _one_pass():
        try:
            # 1) Search button
            btn = page.get_by_role("button", name=re.compile(r"search", re.I))
            if not await btn.count():
                # try links as fallback
                btn = page.get_by_role("link", name=re.compile(r"search", re.I))
                if not await btn.count():
                    return None
            btn_el = btn.first
            btn_box = await btn_el.bounding_box()
            if not btn_box:
                return None

            # 2) Try following sibling (fast DOM-relational check)
            try:
                sib = btn_el.locator("xpath=following::*[@role='tablist'][1]")
                if await sib.count():
                    return await sib.first.element_handle()
            except Exception:
                pass

            # 3) Choose nearest tablist below
            tablists = page.get_by_role("tablist")
            n = await tablists.count()
            best = None
            for i in range(n):
                el = tablists.nth(i)
                try:
                    box = await el.bounding_box()
                except Exception:
                    box = None
                if not box:
                    continue
                if box["y"] >= btn_box["y"] + btn_box["height"]:
                    dist = box["y"] - (btn_box["y"] + btn_box["height"])
                    handle = await el.element_handle()
                    if handle:
                        if best is None or dist < best[0]:
                            best = (dist, handle)
            return best[1] if best else None
        except Exception:
            return None

    # retry loop
    while asyncio.get_event_loop().time() < end_time:
        handle = await _one_pass()
        if handle:
            log_playwright_action("✅ Found target tablist below Search (via _find_tablist_below_search)")
            return handle
        await asyncio.sleep(poll_interval)

    log_playwright_action("❌ _find_tablist_below_search: timed out looking for tablist below Search")
    return None

# ---------------- concrete test ----------------
async def test_tablist_children_group(page: Page, website: str) -> Dict[str, Any]:
    """
    Verify: The list below the Search button has role='tablist' and its DIRECT children have role='group'.
    Also run axe-core, save JSON+HTML reports, and log a brief summary.

    More robust: waits for search button, clicks it (if present), waits briefly for DOM to settle,
    and tries multiple attempts to locate the tablist.
    """
    details: List[str] = []

    # Wait for body / H1 (best-effort) so page has started rendering
    try:
        await page.wait_for_selector("body", timeout=3000)
    except Exception:
        pass

    # Expand any UI under Search, if applicable
    try:
        # wait for the button or link to appear (best-effort)
        try:
            await page.wait_for_selector("button:has-text('Search'), a:has-text('Search')", timeout=2500)
        except Exception:
            # not fatal; will try to query
            pass

        btn = page.get_by_role("button", name=re.compile(r"search", re.I))
        if not await btn.count():
            btn = page.get_by_role("link", name=re.compile(r"search", re.I))
        if await btn.count():
            try:
                await btn.first.click()
                details.append("Clicked Search button in nav")
                # wait a little for any revealed UI to settle
                try:
                    await page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    # networkidle can be strict; fallback to short sleep
                    await asyncio.sleep(0.5)
            except Exception as e:
                details.append(f"Could not click Search button: {e}")
        else:
            details.append("Search button not found (no click attempted)")
    except Exception as e:
        details.append(f"Could not click Search button: {e}")

    # Optional H1 check
    try:
        await page.wait_for_selector("h1", timeout=4000)
        h1_texts = [t.lower() for t in await page.locator("h1").all_inner_texts()]
        if any("loop" in t for t in h1_texts):
            details.append("H1 'Loop' found")
    except Exception:
        pass

    # Run axe-core and persist reports (unchanged)
    try:
        axe = await _run_axe(page)
        violations = axe.get("violations", []) if isinstance(axe, dict) else []
        base = f"axe_report_{_ts()}"
        paths = _write_axe_reports(base, axe)
        axe_summary = {
            "violations_count": len(violations),
            "violations": [
                {"id": v.get("id"), "impact": v.get("impact"), "nodes": len(v.get("nodes", []))}
                for v in violations
            ],
            "json_path": paths["json"],
            "html_path": paths["html"],
        }
        log_playwright_action(f"🧪 axe-core ran: {len(violations)} violation(s) found")
        for v in violations[:5]:
            log_playwright_action(f"   - {v.get('id')} ({v.get('impact','unknown')}), nodes={len(v.get('nodes',[]))}")
        details += [f"axe-core scan complete: {len(violations)} violation(s)",
                    f"axe JSON: {paths['json']}",
                    f"axe HTML: {paths['html']}"]
    except Exception as e:
        axe_summary = {"error": f"axe-core run failed: {e}"}
        details.append(f"axe-core run failed: {e}")
        log_playwright_action(f"❌ axe-core run failed: {e}")

    # Locate the specific tablist BELOW Search (retrying a few times)
    tablist_h = None
    try:
        # try a couple of times with increasing patience
        attempts = [(0.5, 0.25), (1.0, 0.25), (2.0, 0.25)]
        for wait_s, poll in attempts:
            tablist_h = await _find_tablist_below_search(page, max_wait_s=wait_s, poll_interval=poll)
            if tablist_h:
                break
        if not tablist_h:
            # final longer-shot attempt
            tablist_h = await _find_tablist_below_search(page, max_wait_s=3.0, poll_interval=0.3)
    except Exception as e:
        details.append(f"Error while locating tablist: {e}")
        tablist_h = None

    if tablist_h is None:
        return {
            "result": "Fail",
            "bug_fixed": False,
            "details": details + ["Could not locate a tablist below the Search button"],
            "axe": axe_summary
        }

    # Check direct children role=group
    try:
        groups = await tablist_h.query_selector_all(":scope > [role='group']")
        group_count = len(groups)
        details.append(f"Found {group_count} direct child(ren) with role='group' under the target tablist")

        bug_fixed = group_count > 0
        details.append("Bug is fixed: at least one role='group' child present" if bug_fixed
                       else "Bug persists: no direct role='group' children under the tablist")

        return {
            "result": "Pass" if bug_fixed else "Fail",
            "bug_fixed": bug_fixed,
            "details": details,
            "axe": axe_summary
        }
    except Exception as e:
        return {
            "result": "Fail",
            "bug_fixed": False,
            "details": details + [f"Error while checking tablist children: {e}"],
            "axe": axe_summary
        }

# ---------------- scenario executor ----------------
async def execute_scenario_with_page(scenario, page: Page, website: str):
    scenario_id = scenario.get("scenario_id", "unknown")
    kind = scenario.get("kind")
    results = {
        "scenario_id": scenario_id,
        "description": scenario.get("description", ""),
        "result": "Pass",
        "details": [],
        "screenshot_path": None,
    }
    try:
        if kind == "a11y_tablist_children_group_check":
            test_out = await test_tablist_children_group(page, website)
            results["result"] = test_out.get("result", "Fail")
            results["details"] = test_out.get("details", [])
            if "bug_fixed" in test_out:
                results["bug_fixed"] = test_out["bug_fixed"]
            if "axe" in test_out:
                results["axe"] = test_out["axe"]
        else:
            _ensure_dir("screenshots")
            shot = os.path.join("screenshots", f"{scenario_id}.png")
            await page.screenshot(path=shot)
            results["screenshot_path"] = shot
            log_playwright_action(f"📸 Saved screenshot for scenario {scenario_id}")

        return results
    except Exception as e:
        results["result"] = "Fail"
        results["details"].append(f"❌ Execution Error: {str(e)}")
        log_agent_error("A11yExec", f"Execution error for scenario {scenario_id}: {str(e)}")
        return results

# ---------------- main agent ----------------
async def playwright_execution_agent(state: dict) -> dict:
    """
    Launch Edge, perform automated MS login if configured,
    then execute scenarios (including axe-core tests & DOM assertions).
    """
    website = state["website"]
    enriched_scenarios = state["enriched_scenarios"]
    auth_config = state.get("auth_config", {}) or {}

    log_agent_start("A11yExec", {
        "website": website,
        "scenarios_count": len(enriched_scenarios),
        "scenario_ids": [s.get("scenario_id", "Unknown") for s in enriched_scenarios],
    })
    log_agent_thinking("A11yExec", "Called by Orchestrator → running accessibility scenarios")

    results = []
    pw = None
    browser = None
    context = None

    try:
        auth_type = (auth_config.get("type") or "").lower()
        use_headless = False if auth_type in ("mslogin", "interactive") else True
        log_playwright_action(f"🎭 Launching Microsoft Edge with headless={use_headless}")

        pw = await async_playwright().start()
        browser = await pw.chromium.launch(channel="msedge", headless=use_headless)

        # ⛳ IMPORTANT: bypass CSP to reduce injection failures (still inject by SOURCE)
        context = await browser.new_context(bypass_csp=True)
        page = await context.new_page()

        await page.goto(website)
        await page.wait_for_load_state("domcontentloaded")

        ms_page = await click_sign_in_and_capture_ms_page(page)
        if not ms_page:
            log_agent_error("A11yExec", "❌ Could not open Microsoft login page after clicking Sign In")
            return {"execution_results": []}

        if auth_type == "mslogin":
            username = auth_config.get("username")
            password = auth_config.get("password")
            if not username or not password:
                log_agent_error("A11yExec", "❌ mslogin requires username and password in auth_config")
                return {"execution_results": []}
            log_playwright_action("⏳ Waiting for Microsoft login host in popup/tab…")
            while "login.microsoftonline.com" not in (ms_page.url or ""):
                await asyncio.sleep(0.25)
            log_playwright_action(f"🌐 MS login page URL: {ms_page.url}")

            await ms_login(ms_page, username, password)
            ok = await finalize_auth_after_popup(ms_page, page, website)
            if not ok:
                return {"execution_results": []}

            _ensure_dir("artifacts")
            after_login_path = os.path.join("artifacts", f"after_login_{_ts()}.png")
            await page.screenshot(path=after_login_path)
            log_playwright_action(f"📸 Saved screenshot after login ({after_login_path})")

        elif auth_type == "interactive":
            log_playwright_action("🧑‍💻 Interactive login: finish in popup/tab.")
            ok = await finalize_auth_after_popup(ms_page, page, website, timeout_seconds=900)
            if not ok:
                return {"execution_results": []}
        else:
            log_playwright_action("🔓 No authentication configured; continuing without login.")

        for i, scenario in enumerate(enriched_scenarios, 1):
            log_agent_thinking("A11yExec", f"➡️ Running scenario {i}/{len(enriched_scenarios)}: {scenario.get('scenario_id')}")
            res = await execute_scenario_with_page(scenario, page, website)
            results.append(res)

        passed = sum(1 for r in results if r["result"] == "Pass")
        failed = len(results) - passed
        log_agent_complete("A11yExec", {
            "total_scenarios": len(results),
            "passed": passed,
            "failed": failed,
            "website": website,
        })
        return {"execution_results": results}

    except Exception as e:
        log_agent_error("A11yExec", f"Error in playwright_execution_agent: {str(e)}")
        return {"execution_results": []}

    finally:
        try:
            if context: await context.close()
        except Exception: pass
        try:
            if browser: await browser.close()
        except Exception: pass
        try:
            if pw: await pw.stop()
        except Exception: pass
