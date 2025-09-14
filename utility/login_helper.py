# utility/login_helper.py

# ---------------- MS login helpers ----------------
import asyncio
import re
from typing import Optional
from playwright.async_api import async_playwright, Page
from logging_config import (log_playwright_action)


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