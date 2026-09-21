import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
test("review findings and generate a source-backed report", async ({
  page,
}, testInfo) => {
  const email = "analysis-" + Date.now() + "@example.org";
  await page.request.post("/api/auth/register", {
    data: { name: "Test Researcher", email, password: "research-test-pass" },
  });
  const created = await page.request.post("/api/projects", {
    data: {
      title: "Browser analysis fixture",
      question: "What methods and limitations appear in this test corpus?",
    },
  });
  const { id } = await created.json();
  await page.request.post("/api/projects/" + id + "/upload", {
    multipart: {
      file: {
        name: "Synthetic evidence fixture.pdf",
        mimeType: "application/pdf",
        buffer: readFileSync("tests/fixture.pdf"),
      },
    },
  });
  execFileSync(
    process.platform === "win32" ? ".venv/Scripts/python.exe" : "python",
    ["-m", "tests.seed_analysis", id],
  );
  await page.goto("/#research/" + id);
  await expect(page.locator(".answer-content")).toContainText(
    "We evaluated retrieval augmented generation",
  );
  await page.locator(".citations button").first().click();
  await expect(page.getByRole("dialog")).toContainText("The finding");
  await page.getByRole("button", { name: "supported", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "supported", exact: true }),
  ).toHaveClass("active");
  await page.keyboard.press("Escape");

  await page
    .getByRole("button", { name: "Research gaps", exact: true })
    .click();
  await expect(page.locator(".gaps-list")).toContainText(
    "multilingual evaluation",
  );
  await page.getByRole("button", {name: "Compare", exact: true}).click();
  await expect(page.getByRole("region", {name: "Paper comparison"})).toContainText("Method");
  await page.screenshot({path: testInfo.outputPath("comparison-desktop.png"), fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.screenshot({path: testInfo.outputPath("comparison-mobile.png"), fullPage: true});
  await page.setViewportSize({width: 1440, height: 1000});
  await page.getByRole("button", {name: "Generate report", exact: true}).click();
  await expect
    .poll(async () => {
      const r = await page.request.get("/api/projects/" + id);
      return (await r.json()).report;
    })
    .toContain("References");
  const response = await page.request.get("/api/projects/" + id + "/export");
  expect(await response.text()).toContain("Review: supported");
  await expect(page.getByLabel("Download research")).toBeVisible();
  await page.getByRole("button", {name: "Sources", exact: false}).first().click();
  const selected = page.getByRole("checkbox").first();
  await selected.uncheck();
  await expect(page.getByRole("button", {name: "Analyze selected papers"})).toBeDisabled();
  await selected.check();
  await page.getByRole("button", {name: "Analyze selected papers"}).click();
  await expect(page.getByLabel("Download research")).toBeVisible({timeout: 20000});
  await page.getByRole("button", {name: "Delete this research", exact: true}).click();
  await page.getByRole("button", {name: "Delete permanently"}).click();
  await expect(page.getByRole("heading", {name: "What are we curious about today?"})).toBeVisible();
});
