import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from news_kg import load_latest_articles_from_rss, run


OUTPUT_PATH = Path("backend/output/news1_kg.json")


HTML = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Beyond News 임시 뷰어</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 20px; }
    h1 { margin: 0 0 12px; font-size: 22px; }
    .row { display: flex; gap: 16px; flex-wrap: wrap; }
    #network { width: 900px; height: 600px; border: 1px solid #ddd; border-radius: 8px; background: #fff; }
    .panel { flex: 1; min-width: 280px; max-width: 420px; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
    button { padding: 8px 12px; border: 0; border-radius: 6px; background: #111; color: white; cursor: pointer; }
    code { background: #f5f5f5; padding: 2px 6px; border-radius: 4px; }
    ul { padding-left: 18px; }
    .muted { color: #666; font-size: 13px; }
  </style>
</head>
<body>
  <h1>Beyond News 지식그래프 임시 뷰어</h1>
  <div class="card">
    <label for="articleSelect"><strong>최신 기사 3개 중 선택</strong></label>
    <select id="articleSelect"></select>
    <button id="refreshBtn">선택한 기사로 그래프 생성</button>
    <span class="muted">기사 선택 후 버튼 클릭</span>
  </div>

  <div class="row">
    <div id="network"></div>
    <div class="panel">
      <div class="card">
        <div><strong>기사 제목</strong></div>
        <div id="title">-</div>
      </div>
      <div class="card">
        <div><strong>원문 링크</strong></div>
        <a id="link" href="#" target="_blank" rel="noreferrer">-</a>
      </div>
      <div class="card">
        <div><strong>통계</strong></div>
        <ul>
          <li>노드: <code id="nodesCount">0</code></li>
          <li>엣지: <code id="edgesCount">0</code></li>
          <li>RSS: <code id="rssUrl">-</code></li>
        </ul>
      </div>
    </div>
  </div>

  <script>
    let network;

    function nodeColor(type) {
      if (type === "PERSON") return "#ffe082";
      if (type === "ORG") return "#80cbc4";
      if (type === "LOCATION") return "#90caf9";
      return "#d1c4e9";
    }

    async function loadArticles() {
      const res = await fetch("/api/articles");
      const data = await res.json();
      const select = document.getElementById("articleSelect");
      select.innerHTML = "";
      data.articles.forEach(article => {
        const option = document.createElement("option");
        option.value = article.index;
        option.textContent = `[${article.index}] ${article.title}`;
        select.appendChild(option);
      });
    }

    async function loadGraph(articleIndex = 0) {
      const res = await fetch(`/api/graph?article_index=${articleIndex}`);
      const data = await res.json();

      document.getElementById("title").textContent = data.meta.article.title || "-";
      const linkEl = document.getElementById("link");
      linkEl.textContent = data.meta.article.link || "-";
      linkEl.href = data.meta.article.link || "#";
      document.getElementById("nodesCount").textContent = data.nodes.length;
      document.getElementById("edgesCount").textContent = data.edges.length;
      document.getElementById("rssUrl").textContent = data.meta.rss_url || "-";

      const nodes = data.nodes.map(n => ({
        id: n.id,
        label: n.label,
        title: `${n.label} (${n.type})`,
        color: nodeColor(n.type)
      }));
      const edges = data.edges.map(e => ({
        from: e.source,
        to: e.target,
        label: e.relation,
        arrows: "to"
      }));

      const container = document.getElementById("network");
      const graphData = { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) };
      const options = {
        physics: { stabilization: true },
        edges: { font: { size: 10 }, smooth: true },
        nodes: { shape: "dot", size: 16, font: { size: 12 } }
      };

      if (network) network.destroy();
      network = new vis.Network(container, graphData, options);
    }

    async function refreshGraph() {
      const select = document.getElementById("articleSelect");
      const idx = select.value || "0";
      await fetch(`/api/refresh?article_index=${idx}`, { method: "POST" });
      await loadGraph(idx);
    }

    document.getElementById("refreshBtn").addEventListener("click", refreshGraph);
    document.getElementById("articleSelect").addEventListener("change", refreshGraph);
    loadArticles().then(() => loadGraph(0));
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(HTML)
            return
        if parsed.path == "/health":
            self._send_json({"status": "ok"})
            return
        if parsed.path == "/api/articles":
            rss_url, articles = load_latest_articles_from_rss(limit=3)
            self._send_json(
                {
                    "rss_url": rss_url,
                    "articles": [
                        {
                            "index": idx,
                            "title": article["title"],
                            "link": article["link"],
                            "pub_date": article["pub_date"],
                        }
                        for idx, article in enumerate(articles)
                    ],
                }
            )
            return
        if parsed.path == "/api/graph":
            qs = parse_qs(parsed.query)
            article_index = int(qs.get("article_index", ["0"])[0])
            if not OUTPUT_PATH.exists():
                run(str(OUTPUT_PATH), article_index=article_index, article_count=3)
            payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
            current_index = payload.get("meta", {}).get("article_selected_index")
            if current_index != article_index:
                run(str(OUTPUT_PATH), article_index=article_index, article_count=3)
                payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
            self._send_json(payload)
            return
        self._send_json({"error": "not found"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/refresh":
            qs = parse_qs(parsed.query)
            output = qs.get("output", [str(OUTPUT_PATH)])[0]
            article_index = int(qs.get("article_index", ["0"])[0])
            run(output, article_index=article_index, article_count=3)
            payload = json.loads(Path(output).read_text(encoding="utf-8"))
            self._send_json(payload)
            return
        self._send_json({"error": "not found"}, status=404)


def main():
    host = "0.0.0.0"
    port = 8000
    server = HTTPServer((host, port), Handler)
    print(f"Preview server: http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
