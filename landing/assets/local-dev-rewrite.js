/*
 * landing local-dev URL rewrite.
 *
 * При открытии landing'а локально (localhost / 127.0.0.1 / file://) —
 * заменяет production ссылки на cabinet/api/landing-внутренние на localhost.
 * В проде (host = optimyzer.pro и т.п.) — оставляет как есть.
 *
 * Использование в HTML:
 *   <a href="https://account.optimyzer.pro/subscription"
 *      data-cabinet-link data-cabinet-path="/subscription">Купить</a>
 *   <script src="/assets/local-dev-rewrite.js"></script>  (в самом конце body)
 */
(function () {
  var host = location.hostname;
  var isLocal = !host || host === "localhost" || host === "127.0.0.1" || host === "0.0.0.0";
  if (!isLocal) return;
  var CABINET = "http://localhost:5173";
  var API = "http://localhost:8001";
  document.querySelectorAll("[data-cabinet-link]").forEach(function (a) {
    var path = a.getAttribute("data-cabinet-path") || "";
    a.href = CABINET + path;
  });
  document.querySelectorAll("[data-api-link]").forEach(function (a) {
    var path = a.getAttribute("data-api-path") || "";
    a.href = API + path;
  });
})();
