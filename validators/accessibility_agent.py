# agents/accessibility_agent.py
"""
Accessibility testing agent with comprehensive ARIA label validation and bug fixing.

This agent provides:
1. Basic axe-core accessibility testing
2. Specific tablist children group testing
3. Comprehensive ARIA label detection and validation
4. Automatic ARIA label bug fixing
5. Combined test-and-fix workflows

New ARIA Testing Capabilities:
- Detects buttons without accessible names
- Identifies form inputs without proper labels
- Finds links with poor or missing descriptive text
- Checks images without alt text
- Identifies redundant or incorrect ARIA roles
- Automatically attempts to fix detected issues
- Provides before/after metrics and validation

Supported scenario kinds:
- "a11y_tablist_children_group_check": Original tablist testing
- "a11y_aria_labels_comprehensive": Comprehensive ARIA detection only
- "a11y_aria_labels_fix": ARIA bug fixing only
- "a11y_aria_labels_test_and_fix": Combined detection, fixing, and validation
"""
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
from utility.login_helper import click_sign_in_and_capture_ms_page, ms_login

LOOP_URL_HOST = "local.loop.microsoft.com"

def _ts() -> str:
    """Generate timestamp string for file naming"""
    return datetime.now().strftime("%Y%m%d-%H%M%S")

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
async def test_aria_labels_comprehensive(page: Page, website: str) -> Dict[str, Any]:
    """
    Comprehensive ARIA label testing and bug detection.
    Tests for missing or inadequate ARIA labels on interactive elements.
    """
    details: List[str] = []
    issues: List[str] = []
    fixes_applied: List[str] = []

    try:
        # Wait for page to be ready
        await page.wait_for_selector("body", timeout=3000)
        
        # Run axe-core first for baseline accessibility violations
        try:
            axe = await _run_axe(page)
            violations = axe.get("violations", []) if isinstance(axe, dict) else []
            base = f"axe_report_aria_{_ts()}"
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
            details.append(f"axe-core baseline: {len(violations)} violation(s)")
        except Exception as e:
            axe_summary = {"error": f"axe-core run failed: {e}"}
            details.append(f"axe-core baseline failed: {e}")

        # Test 1: Check buttons without accessible names
        buttons_without_labels = await page.evaluate("""
            () => {
                const buttons = Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"], input[type="reset"]'));
                return buttons.filter(btn => {
                    const hasAriaLabel = btn.getAttribute('aria-label') && btn.getAttribute('aria-label').trim();
                    const hasAriaLabelledby = btn.getAttribute('aria-labelledby');
                    const hasVisibleText = btn.textContent && btn.textContent.trim();
                    const hasValue = btn.value && btn.value.trim();
                    const hasTitle = btn.title && btn.title.trim();
                    
                    return !hasAriaLabel && !hasAriaLabelledby && !hasVisibleText && !hasValue && !hasTitle;
                }).map(btn => ({
                    tagName: btn.tagName.toLowerCase(),
                    type: btn.type || 'button',
                    id: btn.id || null,
                    className: btn.className || null,
                    selector: btn.id ? `#${btn.id}` : `${btn.tagName.toLowerCase()}${btn.className ? '.' + btn.className.split(' ').join('.') : ''}`,
                    location: `${btn.getBoundingClientRect().top},${btn.getBoundingClientRect().left}`
                }));
            }
        """)
        
        if buttons_without_labels:
            issues.append(f"Found {len(buttons_without_labels)} button(s) without accessible names")
            details.extend([f"  - Button at {btn['location']}: {btn['selector']}" for btn in buttons_without_labels[:5]])
            if len(buttons_without_labels) > 5:
                details.append(f"  ... and {len(buttons_without_labels) - 5} more")

        # Test 2: Check form inputs without labels
        unlabeled_inputs = await page.evaluate("""
            () => {
                const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="button"]):not([type="submit"]):not([type="reset"]), textarea, select'));
                return inputs.filter(input => {
                    const hasAriaLabel = input.getAttribute('aria-label') && input.getAttribute('aria-label').trim();
                    const hasAriaLabelledby = input.getAttribute('aria-labelledby');
                    const hasLabel = document.querySelector(`label[for="${input.id}"]`) && input.id;
                    const hasPlaceholder = input.placeholder && input.placeholder.trim();
                    const hasTitle = input.title && input.title.trim();
                    
                    return !hasAriaLabel && !hasAriaLabelledby && !hasLabel && !hasPlaceholder && !hasTitle;
                }).map(input => ({
                    tagName: input.tagName.toLowerCase(),
                    type: input.type || 'text',
                    id: input.id || null,
                    name: input.name || null,
                    selector: input.id ? `#${input.id}` : `${input.tagName.toLowerCase()}${input.name ? `[name="${input.name}"]` : ''}`,
                    location: `${input.getBoundingClientRect().top},${input.getBoundingClientRect().left}`
                }));
            }
        """)
        
        if unlabeled_inputs:
            issues.append(f"Found {len(unlabeled_inputs)} form input(s) without labels")
            details.extend([f"  - Input at {inp['location']}: {inp['selector']}" for inp in unlabeled_inputs[:5]])
            if len(unlabeled_inputs) > 5:
                details.append(f"  ... and {len(unlabeled_inputs) - 5} more")

        # Test 3: Check links without descriptive text
        poor_links = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                return links.filter(link => {
                    const hasAriaLabel = link.getAttribute('aria-label') && link.getAttribute('aria-label').trim();
                    const hasAriaLabelledby = link.getAttribute('aria-labelledby');
                    const text = link.textContent && link.textContent.trim();
                    const hasTitle = link.title && link.title.trim();
                    
                    // Check for poor link text
                    const poorTexts = ['click here', 'read more', 'more', 'link', 'here', ''];
                    const isPoorText = !text || poorTexts.includes(text.toLowerCase()) || text.length < 4;
                    
                    return isPoorText && !hasAriaLabel && !hasAriaLabelledby && !hasTitle;
                }).map(link => ({
                    href: link.href,
                    text: link.textContent.trim(),
                    title: link.title || null,
                    selector: link.id ? `#${link.id}` : `a[href="${link.getAttribute('href')}"]`,
                    location: `${link.getBoundingClientRect().top},${link.getBoundingClientRect().left}`
                }));
            }
        """)
        
        if poor_links:
            issues.append(f"Found {len(poor_links)} link(s) with poor or missing descriptive text")
            details.extend([f"  - Link '{link['text']}' at {link['location']}" for link in poor_links[:5]])
            if len(poor_links) > 5:
                details.append(f"  ... and {len(poor_links) - 5} more")

        # Test 4: Check images without alt text
        images_without_alt = await page.evaluate("""
            () => {
                const images = Array.from(document.querySelectorAll('img'));
                return images.filter(img => {
                    const hasAlt = img.getAttribute('alt') !== null;
                    const hasAriaLabel = img.getAttribute('aria-label') && img.getAttribute('aria-label').trim();
                    const hasAriaLabelledby = img.getAttribute('aria-labelledby');
                    const isDecorative = img.getAttribute('role') === 'presentation' || img.getAttribute('role') === 'none';
                    
                    return !hasAlt && !hasAriaLabel && !hasAriaLabelledby && !isDecorative;
                }).map(img => ({
                    src: img.src,
                    id: img.id || null,
                    selector: img.id ? `#${img.id}` : `img[src*="${img.src.split('/').pop()}"]`,
                    location: `${img.getBoundingClientRect().top},${img.getBoundingClientRect().left}`
                }));
            }
        """)
        
        if images_without_alt:
            issues.append(f"Found {len(images_without_alt)} image(s) without alt text")
            details.extend([f"  - Image at {img['location']}: {img['selector']}" for img in images_without_alt[:5]])
            if len(images_without_alt) > 5:
                details.append(f"  ... and {len(images_without_alt) - 5} more")

        # Test 5: Check for redundant or incorrect ARIA roles
        redundant_roles = await page.evaluate("""
            () => {
                const elements = Array.from(document.querySelectorAll('[role]'));
                return elements.filter(el => {
                    const role = el.getAttribute('role');
                    const tagName = el.tagName.toLowerCase();
                    
                    // Check for redundant roles
                    const redundantPairs = {
                        'button': ['button'],
                        'link': ['a'],
                        'heading': ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'],
                        'textbox': ['input'],
                        'list': ['ul', 'ol'],
                        'listitem': ['li']
                    };
                    
                    return redundantPairs[role] && redundantPairs[role].includes(tagName);
                }).map(el => ({
                    tagName: el.tagName.toLowerCase(),
                    role: el.getAttribute('role'),
                    id: el.id || null,
                    selector: el.id ? `#${el.id}` : `${el.tagName.toLowerCase()}[role="${el.getAttribute('role')}"]`,
                    location: `${el.getBoundingClientRect().top},${el.getBoundingClientRect().left}`
                }));
            }
        """)
        
        if redundant_roles:
            issues.append(f"Found {len(redundant_roles)} element(s) with redundant ARIA roles")
            details.extend([f"  - {role['tagName']} with role='{role['role']}' at {role['location']}" for role in redundant_roles[:5]])

        # Summary
        total_issues = len(buttons_without_labels) + len(unlabeled_inputs) + len(poor_links) + len(images_without_alt) + len(redundant_roles)
        details.insert(0, f"ARIA Label Comprehensive Test completed - {total_issues} total issues found")

        result = "Pass" if total_issues == 0 else "Fail"
        
        return {
            "result": result,
            "bug_fixed": total_issues == 0,
            "details": details,
            "issues": issues,
            "fixes_applied": fixes_applied,
            "issue_breakdown": {
                "buttons_without_labels": len(buttons_without_labels),
                "unlabeled_inputs": len(unlabeled_inputs), 
                "poor_links": len(poor_links),
                "images_without_alt": len(images_without_alt),
                "redundant_roles": len(redundant_roles)
            },
            "axe": axe_summary
        }

    except Exception as e:
        return {
            "result": "Fail",
            "bug_fixed": False,
            "details": details + [f"Error during ARIA label testing: {e}"],
            "issues": issues,
            "fixes_applied": fixes_applied,
            "axe": axe_summary if 'axe_summary' in locals() else {"error": "axe not run"}
        }

async def fix_aria_label_issues(page: Page, website: str) -> Dict[str, Any]:
    """
    Attempt to automatically fix common ARIA label issues by adding appropriate labels.
    This function tries to intelligently add ARIA labels based on context.
    """
    details: List[str] = []
    fixes_applied: List[str] = []
    failed_fixes: List[str] = []

    try:
        # Fix 1: Add aria-label to buttons without accessible names
        buttons_fixed = await page.evaluate("""
            () => {
                const buttons = Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"], input[type="reset"]'));
                let fixed = 0;
                
                buttons.forEach(btn => {
                    const hasAriaLabel = btn.getAttribute('aria-label') && btn.getAttribute('aria-label').trim();
                    const hasAriaLabelledby = btn.getAttribute('aria-labelledby');
                    const hasVisibleText = btn.textContent && btn.textContent.trim();
                    const hasValue = btn.value && btn.value.trim();
                    const hasTitle = btn.title && btn.title.trim();
                    
                    if (!hasAriaLabel && !hasAriaLabelledby && !hasVisibleText && !hasValue && !hasTitle) {
                        // Try to generate an appropriate label
                        let label = '';
                        
                        // Check for icon classes that might indicate purpose
                        if (btn.className.includes('search')) label = 'Search';
                        else if (btn.className.includes('close') || btn.className.includes('dismiss')) label = 'Close';
                        else if (btn.className.includes('menu') || btn.className.includes('hamburger')) label = 'Menu';
                        else if (btn.className.includes('submit')) label = 'Submit';
                        else if (btn.className.includes('save')) label = 'Save';
                        else if (btn.className.includes('delete') || btn.className.includes('remove')) label = 'Delete';
                        else if (btn.className.includes('edit')) label = 'Edit';
                        else if (btn.className.includes('add') || btn.className.includes('plus')) label = 'Add';
                        else if (btn.type === 'submit') label = 'Submit form';
                        else if (btn.type === 'reset') label = 'Reset form';
                        else {
                            // Check parent context
                            const parent = btn.closest('form, nav, header, footer, main, section');
                            if (parent) {
                                const parentRole = parent.getAttribute('role');
                                if (parentRole === 'navigation' || parent.tagName === 'NAV') label = 'Navigation button';
                                else if (parent.tagName === 'FORM') label = 'Form button';
                                else label = 'Action button';
                            } else {
                                label = 'Button';
                            }
                        }
                        
                        if (label) {
                            btn.setAttribute('aria-label', label);
                            fixed++;
                        }
                    }
                });
                
                return fixed;
            }
        """)
        
        if buttons_fixed > 0:
            fixes_applied.append(f"Added aria-label to {buttons_fixed} button(s)")

        # Fix 2: Add labels to form inputs
        inputs_fixed = await page.evaluate("""
            () => {
                const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="button"]):not([type="submit"]):not([type="reset"]), textarea, select'));
                let fixed = 0;
                
                inputs.forEach(input => {
                    const hasAriaLabel = input.getAttribute('aria-label') && input.getAttribute('aria-label').trim();
                    const hasAriaLabelledby = input.getAttribute('aria-labelledby');
                    const hasLabel = document.querySelector(`label[for="${input.id}"]`) && input.id;
                    const hasPlaceholder = input.placeholder && input.placeholder.trim();
                    const hasTitle = input.title && input.title.trim();
                    
                    if (!hasAriaLabel && !hasAriaLabelledby && !hasLabel && !hasPlaceholder && !hasTitle) {
                        let label = '';
                        
                        // Try to infer label from context
                        if (input.name) {
                            label = input.name.replace(/[_-]/g, ' ').replace(/([A-Z])/g, ' $1').trim();
                            label = label.charAt(0).toUpperCase() + label.slice(1);
                        } else if (input.id) {
                            label = input.id.replace(/[_-]/g, ' ').replace(/([A-Z])/g, ' $1').trim();
                            label = label.charAt(0).toUpperCase() + label.slice(1);
                        } else {
                            // Check input type
                            switch (input.type) {
                                case 'email': label = 'Email address'; break;
                                case 'password': label = 'Password'; break;
                                case 'tel': label = 'Phone number'; break;
                                case 'url': label = 'Website URL'; break;
                                case 'search': label = 'Search'; break;
                                case 'number': label = 'Number'; break;
                                case 'date': label = 'Date'; break;
                                case 'time': label = 'Time'; break;
                                case 'checkbox': label = 'Checkbox'; break;
                                case 'radio': label = 'Radio option'; break;
                                default:
                                    if (input.tagName === 'TEXTAREA') label = 'Text area';
                                    else if (input.tagName === 'SELECT') label = 'Select option';
                                    else label = 'Text input';
                            }
                        }
                        
                        if (label) {
                            input.setAttribute('aria-label', label);
                            fixed++;
                        }
                    }
                });
                
                return fixed;
            }
        """)
        
        if inputs_fixed > 0:
            fixes_applied.append(f"Added aria-label to {inputs_fixed} form input(s)")

        # Fix 3: Improve link descriptions
        links_fixed = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                let fixed = 0;
                
                links.forEach(link => {
                    const hasAriaLabel = link.getAttribute('aria-label') && link.getAttribute('aria-label').trim();
                    const hasAriaLabelledby = link.getAttribute('aria-labelledby');
                    const text = link.textContent && link.textContent.trim();
                    const hasTitle = link.title && link.title.trim();
                    
                    const poorTexts = ['click here', 'read more', 'more', 'link', 'here', ''];
                    const isPoorText = !text || poorTexts.includes(text.toLowerCase()) || text.length < 4;
                    
                    if (isPoorText && !hasAriaLabel && !hasAriaLabelledby && !hasTitle) {
                        let label = '';
                        
                        // Try to get context from nearby elements
                        const nearbyText = [];
                        
                        // Check previous sibling text
                        const prevSibling = link.previousElementSibling;
                        if (prevSibling && prevSibling.textContent) {
                            nearbyText.push(prevSibling.textContent.trim());
                        }
                        
                        // Check parent text (excluding the link itself)
                        const parent = link.parentElement;
                        if (parent) {
                            const parentText = parent.textContent.replace(link.textContent, '').trim();
                            if (parentText && parentText.length > 0) {
                                nearbyText.push(parentText);
                            }
                        }
                        
                        // Use href as fallback
                        const href = link.getAttribute('href');
                        if (href && href !== '#') {
                            if (href.startsWith('mailto:')) {
                                label = `Email ${href.replace('mailto:', '')}`;
                            } else if (href.startsWith('tel:')) {
                                label = `Call ${href.replace('tel:', '')}`;
                            } else if (href.includes('download')) {
                                label = 'Download file';
                            } else {
                                // Use the best nearby text or generate from URL
                                if (nearbyText.length > 0) {
                                    label = nearbyText[0].substring(0, 50);
                                } else {
                                    try {
                                        const url = new URL(href, window.location.href);
                                        const path = url.pathname.split('/').pop() || url.hostname;
                                        label = `Link to ${path}`;
                                    } catch (e) {
                                        label = 'External link';
                                    }
                                }
                            }
                        } else {
                            label = 'Link';
                        }
                        
                        if (label && label.length > 0) {
                            link.setAttribute('aria-label', label);
                            fixed++;
                        }
                    }
                });
                
                return fixed;
            }
        """)
        
        if links_fixed > 0:
            fixes_applied.append(f"Improved descriptions for {links_fixed} link(s)")

        # Fix 4: Add alt text to images
        images_fixed = await page.evaluate("""
            () => {
                const images = Array.from(document.querySelectorAll('img'));
                let fixed = 0;
                
                images.forEach(img => {
                    const hasAlt = img.getAttribute('alt') !== null;
                    const hasAriaLabel = img.getAttribute('aria-label') && img.getAttribute('aria-label').trim();
                    const hasAriaLabelledby = img.getAttribute('aria-labelledby');
                    const isDecorative = img.getAttribute('role') === 'presentation' || img.getAttribute('role') === 'none';
                    
                    if (!hasAlt && !hasAriaLabel && !hasAriaLabelledby && !isDecorative) {
                        let altText = '';
                        
                        // Try to generate alt text from src or context
                        const src = img.src;
                        if (src) {
                            const filename = src.split('/').pop().split('.')[0];
                            if (filename) {
                                altText = filename.replace(/[_-]/g, ' ').replace(/([A-Z])/g, ' $1').trim();
                                altText = altText.charAt(0).toUpperCase() + altText.slice(1);
                            }
                        }
                        
                        // Check for common icon/logo patterns
                        if (img.className.includes('logo')) altText = 'Logo';
                        else if (img.className.includes('icon')) altText = 'Icon';
                        else if (img.className.includes('avatar')) altText = 'User avatar';
                        else if (!altText) altText = 'Image';
                        
                        img.setAttribute('alt', altText);
                        fixed++;
                    }
                });
                
                return fixed;
            }
        """)
        
        if images_fixed > 0:
            fixes_applied.append(f"Added alt text to {images_fixed} image(s)")

        # Fix 5: Remove redundant ARIA roles
        redundant_fixed = await page.evaluate("""
            () => {
                const elements = Array.from(document.querySelectorAll('[role]'));
                let fixed = 0;
                
                elements.forEach(el => {
                    const role = el.getAttribute('role');
                    const tagName = el.tagName.toLowerCase();
                    
                    const redundantPairs = {
                        'button': ['button'],
                        'link': ['a'],
                        'heading': ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'],
                        'textbox': ['input'],
                        'list': ['ul', 'ol'],
                        'listitem': ['li']
                    };
                    
                    if (redundantPairs[role] && redundantPairs[role].includes(tagName)) {
                        el.removeAttribute('role');
                        fixed++;
                    }
                });
                
                return fixed;
            }
        """)
        
        if redundant_fixed > 0:
            fixes_applied.append(f"Removed {redundant_fixed} redundant ARIA role(s)")

        details.append(f"ARIA Label Bug Fixing completed - {len(fixes_applied)} types of fixes applied")
        details.extend(fixes_applied)
        
        if failed_fixes:
            details.append("Failed fixes:")
            details.extend(failed_fixes)

        return {
            "result": "Pass" if len(fixes_applied) > 0 else "Fail",
            "bug_fixed": len(fixes_applied) > 0,
            "details": details,
            "fixes_applied": fixes_applied,
            "failed_fixes": failed_fixes,
            "fix_count": {
                "buttons": buttons_fixed,
                "inputs": inputs_fixed,
                "links": links_fixed,
                "images": images_fixed,
                "redundant_roles": redundant_fixed
            }
        }

    except Exception as e:
        return {
            "result": "Fail",
            "bug_fixed": False,
            "details": details + [f"Error during ARIA label fixing: {e}"],
            "fixes_applied": fixes_applied,
            "failed_fixes": failed_fixes + [f"Critical error: {e}"]
        }

async def test_and_fix_aria_labels(page: Page, website: str) -> Dict[str, Any]:
    """
    Comprehensive ARIA label testing with automatic bug fixing.
    This function first detects ARIA issues, then attempts to fix them, and finally validates the fixes.
    """
    details: List[str] = []
    all_issues: List[str] = []
    
    try:
        # Step 1: Run initial detection to identify issues
        details.append("=== ARIA LABEL DETECTION PHASE ===")
        initial_test = await test_aria_labels_comprehensive(page, website)
        initial_issues = initial_test.get("issue_breakdown", {})
        
        total_initial_issues = sum(initial_issues.values()) if initial_issues else 0
        details.append(f"Initial scan found {total_initial_issues} ARIA-related issues:")
        
        for issue_type, count in initial_issues.items():
            if count > 0:
                details.append(f"  - {issue_type.replace('_', ' ').title()}: {count}")
                all_issues.extend(initial_test.get("issues", []))
        
        # Step 2: Apply automatic fixes if issues were found
        fixes_result = {"fixes_applied": [], "fix_count": {}}
        if total_initial_issues > 0:
            details.append("\n=== ARIA LABEL FIXING PHASE ===")
            fixes_result = await fix_aria_label_issues(page, website)
            details.extend(fixes_result.get("details", []))
        else:
            details.append("\n=== NO FIXES NEEDED ===")
            details.append("No ARIA label issues detected, skipping fix phase")
        
        # Step 3: Re-run detection to validate fixes
        details.append("\n=== VALIDATION PHASE ===")
        final_test = await test_aria_labels_comprehensive(page, website)
        final_issues = final_test.get("issue_breakdown", {})
        
        total_final_issues = sum(final_issues.values()) if final_issues else 0
        issues_fixed = total_initial_issues - total_final_issues
        
        details.append(f"Post-fix scan found {total_final_issues} remaining issues")
        details.append(f"Successfully resolved {issues_fixed} issues")
        
        if total_final_issues > 0:
            details.append("Remaining issues:")
            for issue_type, count in final_issues.items():
                if count > 0:
                    details.append(f"  - {issue_type.replace('_', ' ').title()}: {count}")
        
        # Determine overall result
        significant_improvement = issues_fixed >= (total_initial_issues * 0.5)  # Fixed at least 50%
        no_critical_remaining = total_final_issues < 5  # Less than 5 remaining issues
        
        if total_initial_issues == 0:
            result = "Pass"
            bug_status = "No bugs detected"
        elif total_final_issues == 0:
            result = "Pass"
            bug_status = "All bugs fixed"
        elif significant_improvement and no_critical_remaining:
            result = "Pass"
            bug_status = "Significant improvement achieved"
        else:
            result = "Fail"
            bug_status = "Issues remain after attempted fixes"
        
        return {
            "result": result,
            "bug_fixed": total_final_issues < total_initial_issues,
            "details": details,
            "issues": all_issues,
            "fixes_applied": fixes_result.get("fixes_applied", []),
            "bug_status": bug_status,
            "metrics": {
                "initial_issues": total_initial_issues,
                "final_issues": total_final_issues,
                "issues_fixed": issues_fixed,
                "fix_success_rate": (issues_fixed / total_initial_issues * 100) if total_initial_issues > 0 else 100
            },
            "initial_breakdown": initial_issues,
            "final_breakdown": final_issues,
            "axe": final_test.get("axe", {})
        }
        
    except Exception as e:
        return {
            "result": "Fail",
            "bug_fixed": False,
            "details": details + [f"Error in ARIA test and fix process: {e}"],
            "issues": all_issues,
            "fixes_applied": [],
            "bug_status": f"Error occurred: {e}",
            "axe": {"error": "Test failed before axe could run"}
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
        elif kind == "a11y_aria_labels_comprehensive":
            test_out = await test_aria_labels_comprehensive(page, website)
            results["result"] = test_out.get("result", "Fail")
            results["details"] = test_out.get("details", [])
            results["issues"] = test_out.get("issues", [])
            results["issue_breakdown"] = test_out.get("issue_breakdown", {})
            if "bug_fixed" in test_out:
                results["bug_fixed"] = test_out["bug_fixed"]
            if "axe" in test_out:
                results["axe"] = test_out["axe"]
        elif kind == "a11y_aria_labels_fix":
            test_out = await fix_aria_label_issues(page, website)
            results["result"] = test_out.get("result", "Fail")
            results["details"] = test_out.get("details", [])
            results["fixes_applied"] = test_out.get("fixes_applied", [])
            results["fix_count"] = test_out.get("fix_count", {})
            if "bug_fixed" in test_out:
                results["bug_fixed"] = test_out["bug_fixed"]
        elif kind == "a11y_aria_labels_test_and_fix":
            test_out = await test_and_fix_aria_labels(page, website)
            results["result"] = test_out.get("result", "Fail")
            results["details"] = test_out.get("details", [])
            results["issues"] = test_out.get("issues", [])
            results["fixes_applied"] = test_out.get("fixes_applied", [])
            results["bug_status"] = test_out.get("bug_status", "Unknown")
            results["metrics"] = test_out.get("metrics", {})
            results["initial_breakdown"] = test_out.get("initial_breakdown", {})
            results["final_breakdown"] = test_out.get("final_breakdown", {})
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
