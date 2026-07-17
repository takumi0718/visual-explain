/* Test driver: read a JSON list of calls on stdin, run them against the
   engine, print the JSON list of results. "$state" in args is replaced by
   the running state; {assign: true} stores the result back into it. */
const engine = require("./decision_engine.js");
let input = "";
process.stdin.on("data", (chunk) => { input += chunk; });
process.stdin.on("end", () => {
  const calls = JSON.parse(input);
  let state = engine.emptyState();
  const results = [];
  for (const call of calls) {
    const args = (call.args || []).map((a) => (a === "$state" ? state : a));
    const result = engine[call.fn](...args);
    if (call.assign) state = result;
    results.push(result === undefined ? null : result);
  }
  process.stdout.write(JSON.stringify(results));
});
