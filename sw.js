importScripts("./build-meta.js");

const CACHE_PREFIX = "shaoyang-quiz-";
const SHELL_REVISION = "mobile-study-12";
const CACHE_NAME = `${CACHE_PREFIX}${globalThis.SHAOYANG_BUILD?.id || "development"}-${SHELL_REVISION}`;
const NETWORK_TIMEOUT_MS = 4500;
const CORE_ASSETS = [
  "./",
  "./index.html",
  "./quiz.html",
  "./style.css",
  "./build-meta.js",
  "./home-data.js",
  "./home.js",
  "./reset-data.js",
  "./app.js",
  "./question-media.js",
  "./questions.js",
  "./manifest.webmanifest",
  "./icon-192.png",
  "./icon-512.png",
  "./icon.svg",
  "./notes.html",
  "./color-notes.html",
  "./media/ee_series_parallel.svg",
  "./media/ee_kcl_node.svg",
  "./media/ee_rc_response.svg",
  "./media/ee_rlc_phasor.svg",
  "./media/ee_self_hold_control.svg",
  "./media/analog_diode_iv.svg",
  "./media/analog_bjt_states.svg",
  "./media/analog_common_emitter.svg",
  "./media/analog_opamp_inverting.svg",
  "./media/analog_feedback_block.svg",
  "./media/analog_power_supply.svg",
  "./media/digital_comb_seq.svg",
  "./media/digital_kmap.svg",
  "./media/digital_flipflop_timing.svg",
  "./media/digital_counter_states.svg",
  "./media/digital_adc_process.svg",
  "./media/comm_system.svg",
  "./media/comm_sampling.svg",
  "./media/comm_modulation.svg",
  "./media/comm_spectrum.svg",
  "./media/comm_superhet.svg",
  "./media/network_layers.svg",
  "./media/network_subnet.svg",
  "./media/ds_tree_traversal.svg",
  "./media/ds_graph_traversal.svg",
  "./media/ds_complexity_growth.svg",
  "./media/ds_array_linked.svg",
  "./media/ds_stack_queue.svg",
  "./media/ds_kmp_prefix.svg",
  "./media/ds_array_sparse.svg",
  "./media/ds_hash_probe.svg",
  "./media/ds_insertion_sort.svg",
  "./media/ds_algorithm_choice.svg",
  "./media/os_process_states.svg",
  "./media/os_rr_timeline.svg",
  "./media/os_semaphore_buffer.svg",
  "./media/os_paging_address.svg",
  "./media/os_io_disk.svg",
  "./media/computer_memory_hierarchy.svg",
  "./media/db_relationships.svg",
  "./media/db_er_symbols.svg",
  "./media/db_sql_order.svg",
  "./media/db_index_choice.svg",
  "./media/db_normalization.svg",
  "./media/db_isolation.svg",
  "./media/db_wal.svg",
  "./media/program_loop_trace.svg",
  "./media/program_pointer.svg",
  "./media/program_function_args.svg",
  "./media/co_instruction_cycle.svg",
  "./media/co_pipeline.svg",
  "./media/co_float_fields.svg",
  "./media/co_cache_address.svg",
  "./media/co_virtual_address.svg",
  "./media/tcp_handshake.svg",
  "./media/tcp_congestion.svg",
  "./media/streaming_buffer.svg",
  "./media/wlan_hidden_station.svg"
];

self.addEventListener("install", (event) => {
  const freshRequests = CORE_ASSETS.map((url) => new Request(url, {cache: "reload"}));
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(freshRequests)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") self.skipWaiting();
});

async function fetchWithTimeout(request) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), NETWORK_TIMEOUT_MS);
  try {
    return await fetch(request, {signal: controller.signal, cache: "no-cache"});
  } finally {
    clearTimeout(timer);
  }
}

async function readFallback(request) {
  try {
    const cache = await caches.open(CACHE_NAME);
    const direct = await cache.match(request, {ignoreSearch: request.mode === "navigate"});
    if (direct) return direct;
    if (request.mode === "navigate") {
      const pathname = new URL(request.url).pathname;
      if (pathname.endsWith("/color-notes.html")) return await cache.match("./color-notes.html", {ignoreSearch: true});
      if (pathname.endsWith("/notes.html")) return await cache.match("./notes.html", {ignoreSearch: true});
      if (pathname.endsWith("/quiz.html")) return await cache.match("./quiz.html", {ignoreSearch: true});
      return await cache.match("./index.html", {ignoreSearch: true});
    }
  } catch {}
  return null;
}

async function cacheResponse(request, response) {
  if (!response || !response.ok) return;
  try {
    const cache = await caches.open(CACHE_NAME);
    await cache.put(request, response.clone());
  } catch {}
}

async function networkFirst(request) {
  try {
    const response = await fetchWithTimeout(request);
    await cacheResponse(request, response);
    return response;
  } catch {
    return (await readFallback(request)) || Response.error();
  }
}

async function cacheFirst(request) {
  const cached = await readFallback(request);
  if (cached) return cached;
  const response = await fetch(request);
  await cacheResponse(request, response);
  return response;
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.pathname.includes("/api/")) return;

  if (request.mode === "navigate") {
    event.respondWith(networkFirst(request));
    return;
  }
  const isCritical = /\/(questions\.js|home-data\.js|(?:color-)?notes\.html|quiz\.html|app\.js|home\.js)$/.test(url.pathname);
  const isMedia = request.destination === "image";
  event.respondWith(isCritical ? networkFirst(request) : isMedia ? cacheFirst(request) : networkFirst(request));
});
