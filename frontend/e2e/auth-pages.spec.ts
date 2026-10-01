import { expect, test } from "@playwright/test";

test.describe("Enterprise Auth Split Layout & Registration E2E", () => {
  test("full viewport at 1440px renders 50/50 split layout without horizontal scrollbar", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/signup");

    // Verify main form and hero showcase are both visible on desktop
    const mainCanvas = page.locator("main");
    await expect(mainCanvas).toBeVisible();

    const heroShowcase = page.locator("aside");
    await expect(heroShowcase).toBeVisible();

    // Verify hero text
    await expect(page.getByText("Real-Time Decision Intelligence for African Fintechs")).toBeVisible();
    await expect(page.getByText("Command Canvas")).toBeVisible();
    await expect(page.getByText("Providus Latency")).toBeVisible();

    // Assert no horizontal scrollbar
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
  });

  test("fills out the signup form with full name, username, email, password and registers", async ({ page }) => {
    await page.route("**/api/v1/auth/register", async (route) => {
      const data = route.request().postDataJSON();
      expect(data.full_name).toBe("Babatunde Adeleke");
      expect(data.username).toBe("b_adeleke");
      expect(data.email).toBe("babatunde@fintech.ng");
      expect(data.password).toBe("SecurePassword2026");
      expect(data.confirm_password).toBe("SecurePassword2026");
      expect(data.terms_accepted).toBe(true);

      await route.fulfill({
        status: 201,
        json: {
          access_token: "mock-e2e-jwt-token",
          token_type: "bearer",
          expires_in: 900,
          user: {
            id: "user-uuid",
            tenant_id: "tenant-uuid",
            email: data.email,
            display_name: data.full_name,
            permission_role: "ADMIN",
            stage_a_completed: false,
          },
        },
      });
    });

    await page.goto("/signup");

    // Submit button must be disabled until terms are checked
    const submitBtn = page.locator("#submit_button");
    await expect(submitBtn).toBeDisabled();

    // Fill form
    await page.locator("#full_name").fill("Babatunde Adeleke");
    await page.locator("#username").fill("b_adeleke");
    await page.locator("#email").fill("babatunde@fintech.ng");
    await page.locator("#password").fill("SecurePassword2026");
    await page.locator("#confirm_password").fill("SecurePassword2026");

    // Passwords match notification
    await expect(page.getByText("Passwords match")).toBeVisible();

    // Check terms
    await page.locator("#terms_accepted").check();
    await expect(submitBtn).toBeEnabled();

    // Submit and navigate
    await submitBtn.click();
    await expect(page).toHaveURL(/\/onboarding\/stage-a/);
  });

  test("forgot password link navigates from signup/login to /forgot-password", async ({ page }) => {
    await page.goto("/signup");
    await page.getByRole("link", { name: "Forgot password?" }).click();
    await expect(page).toHaveURL(/\/forgot-password/);
    await expect(page.getByRole("heading", { name: "Forgot Password" })).toBeVisible();
  });
});
