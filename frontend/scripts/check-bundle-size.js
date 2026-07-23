import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";

function readMaximumKilobytes(arguments_) {
  const inlineArgument = arguments_.find((argument) => argument.startsWith("--max-kb="));
  const separateArgumentIndex = arguments_.indexOf("--max-kb");
  const rawValue = inlineArgument?.split("=", 2)[1]
    ?? (separateArgumentIndex >= 0 ? arguments_[separateArgumentIndex + 1] : undefined);
  const maximumKilobytes = Number(rawValue);

  if (!Number.isFinite(maximumKilobytes) || maximumKilobytes <= 0) {
    throw new Error("Provide a positive bundle limit with --max-kb=<number>.");
  }

  return maximumKilobytes;
}

function readJson(filePath) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`Missing Next.js build manifest: ${filePath}. Run npm run build first.`);
  }

  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function compressedSize(filePath) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`Bundle manifest references a missing asset: ${filePath}`);
  }

  return zlib.gzipSync(fs.readFileSync(filePath), { level: 9 }).byteLength;
}

function main() {
  const maximumKilobytes = readMaximumKilobytes(process.argv.slice(2));
  const nextDirectory = path.resolve(process.cwd(), ".next");
  const appManifest = readJson(path.join(nextDirectory, "app-build-manifest.json"));
  const buildManifest = readJson(path.join(nextDirectory, "build-manifest.json"));
  const sharedFiles = buildManifest.rootMainFiles ?? [];
  const routes = Object.entries(appManifest.pages ?? {});

  if (routes.length === 0) {
    throw new Error("The Next.js app build manifest contains no routes to measure.");
  }

  const routeSizes = routes.map(([route, routeFiles]) => {
    const initialJavaScriptFiles = [
      ...new Set([...sharedFiles, ...routeFiles].filter((file) => file.endsWith(".js")))
    ];
    const bytes = initialJavaScriptFiles.reduce(
      (total, file) => total + compressedSize(path.join(nextDirectory, file)),
      0
    );

    return { route, bytes };
  });

  for (const { route, bytes } of routeSizes) {
    console.log(`${route}: ${(bytes / 1024).toFixed(2)} KB gzipped initial JavaScript`);
  }

  const largestRoute = routeSizes.reduce((largest, route) =>
    route.bytes > largest.bytes ? route : largest
  );
  const maximumBytes = maximumKilobytes * 1024;

  if (largestRoute.bytes > maximumBytes) {
    throw new Error(
      `${largestRoute.route} is ${(largestRoute.bytes / 1024).toFixed(2)} KB gzipped; `
      + `the limit is ${maximumKilobytes.toFixed(2)} KB.`
    );
  }

  console.log(`Bundle size check passed (limit: ${maximumKilobytes.toFixed(2)} KB).`);
}

try {
  main();
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
}
