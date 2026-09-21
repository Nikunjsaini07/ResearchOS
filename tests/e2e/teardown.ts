export default async function teardown() {
  // Let the isolated server exit cleanly on Windows as well as Linux.
  await fetch("http://127.0.0.1:8766/__test_shutdown", {method: "POST"}).catch(() => {});
  for (let attempt = 0; attempt < 40; attempt++) {
    try { await fetch("http://127.0.0.1:8766/api/health"); }
    catch { return; }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
}
