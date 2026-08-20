import http from "node:http";

const hostname = process.env.HEALTHCHECK_HOST ?? "127.0.0.1";
const port = Number.parseInt(process.env.PORT ?? "3000", 10);

if (!Number.isInteger(port) || port < 1 || port > 65535) {
  console.error(`Frontend health check received an invalid PORT: ${process.env.PORT}`);
  process.exit(1);
}

const request = http.get(
  {
    hostname,
    port,
    path: "/",
    timeout: 5_000,
  },
  (response) => {
    response.resume();
    const statusCode = response.statusCode ?? 500;

    if (statusCode < 400) {
      process.exit(0);
    }

    console.error(`Frontend health check returned HTTP ${statusCode}.`);
    process.exit(1);
  },
);

request.once("timeout", () => {
  request.destroy(new Error("Frontend health check timed out."));
});

request.once("error", (error) => {
  console.error(`Frontend health check failed: ${error.message}`);
  process.exit(1);
});
