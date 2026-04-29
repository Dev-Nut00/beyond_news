import argparse
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from typing import Dict, List, Set, Tuple


RSS_CANDIDATES = [
    "https://news.google.com/rss/search?q=site:joongang.co.kr&hl=ko&gl=KR&ceid=KR:ko",
    "https://rss.joins.com/joins_news_list.xml",
]
USER_AGENT = "BeyondNewsBot/0.1 (+https://github.com/Dev-Nut00/beyond_news)"


KOREAN_STOPWORDS = {
    "이번",
    "지난",
    "관련",
    "대한",
    "통해",
    "정도",
    "가운데",
    "뉴스",
    "중앙일보",
    "기자",
    "오전",
    "오후",
    "속보",
    "라고",
    "우리에게",
    "알려와",
}


ORG_SUFFIXES = (
    "부",
    "청",
    "원",
    "처",
    "정부",
    "당",
    "위원회",
    "법원",
    "검찰",
    "경찰",
    "은행",
    "공사",
    "협회",
    "연구원",
)


RELATION_KEYWORDS = {
    "발표했다": ("발표", "밝혔", "설명", "전했", "공개"),
    "조사한다": ("조사", "분석", "점검", "수사"),
    "비판했다": ("비판", "지적", "반박", "우려"),
    "지원한다": ("지원", "협력", "추진", "합의"),
    "요청했다": ("요청", "촉구", "요구", "제안"),
    "경고했다": ("경고", "주의", "강조"),
    "부인했다": ("부인", "해명", "일축"),
}


@dataclass
class Article:
    title: str
    link: str
    pub_date: str
    summary: str
    content: str


def fetch_text(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    with urllib.request.urlopen(req, timeout=8) as res:
        return res.read().decode("utf-8", errors="ignore")


def parse_rss_items(rss_xml: str, limit: int = 3) -> List[Dict[str, str]]:
    root = ET.fromstring(rss_xml)
    items = root.findall(".//item")
    if not items:
        raise RuntimeError("RSS item을 찾지 못했습니다.")
    parsed_items: List[Dict[str, str]] = []
    for item in items[:limit]:
        parsed_items.append(
            {
                "title": (item.findtext("title") or "").strip(),
                "link": (item.findtext("link") or "").strip(),
                "pub_date": (item.findtext("pubDate") or "").strip(),
                "summary": clean_html((item.findtext("description") or "").strip()),
            }
        )
    return parsed_items


def load_latest_articles_from_rss(limit: int = 3) -> Tuple[str, List[Dict[str, str]]]:
    parse_errors = []
    for rss_url in RSS_CANDIDATES:
        try:
            rss_xml = fetch_text(rss_url)
            items = parse_rss_items(rss_xml, limit=limit)
            valid_items = [item for item in items if item["link"]]
            if not valid_items:
                raise RuntimeError("기사 링크가 비어 있습니다.")
            return rss_url, valid_items
        except Exception as e:
            parse_errors.append(f"{rss_url}: {e}")
    raise RuntimeError("RSS 파싱 실패\n" + "\n".join(parse_errors))


def clean_html(raw_html: str) -> str:
    text = re.sub(r"<script.*?>.*?</script>", " ", raw_html, flags=re.I | re.S)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_article_text(page_html: str) -> str:
    # 중앙일보 페이지 구조가 자주 바뀔 수 있어 article/p 태그를 함께 수집한다.
    article_blocks = re.findall(r"<article[^>]*>(.*?)</article>", page_html, flags=re.I | re.S)
    if article_blocks:
        joined = " ".join(clean_html(block) for block in article_blocks)
        if len(joined) > 120:
            return joined

    p_blocks = re.findall(r"<p[^>]*>(.*?)</p>", page_html, flags=re.I | re.S)
    joined_p = " ".join(clean_html(block) for block in p_blocks)
    if len(joined_p) > 120:
        return joined_p

    return clean_html(page_html)[:4000]


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[\.\!\?다])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) > 10]


def classify_entity(token: str) -> str:
    if token.endswith("기자"):
        return "PERSON"
    if token.endswith(ORG_SUFFIXES):
        return "ORG"
    if any(
        loc in token
        for loc in ("서울", "한국", "미국", "중국", "일본", "부산", "인천", "경기", "이란")
    ):
        return "LOCATION"
    return "CONCEPT"


def extract_entities(text: str) -> Dict[str, str]:
    candidates = re.findall(r"[가-힣A-Za-z0-9·\-]{2,20}", text)
    entities: Dict[str, str] = {}
    for token in candidates:
        if token in KOREAN_STOPWORDS:
            continue
        if token.isdigit():
            continue
        if len(token) < 2:
            continue
        ent_type = classify_entity(token)
        entities[token] = ent_type
    return entities


def infer_relation(sentence: str) -> str:
    for rel, words in RELATION_KEYWORDS.items():
        if any(word in sentence for word in words):
            return rel
    return "언급했다"


def build_graph(article: Article, rss_url: str) -> Dict:
    base_text = f"{article.title}. {article.summary}. {article.content}"
    sentences = split_sentences(base_text)

    nodes: Dict[str, Dict] = {}
    edges: Set[Tuple[str, str, str]] = set()

    for sentence in sentences:
        local_entities = extract_entities(sentence)
        labels = list(local_entities.keys())[:8]

        for label, ent_type in local_entities.items():
            if label not in nodes:
                nodes[label] = {"id": label, "label": label, "type": ent_type}

        if len(labels) >= 2:
            rel = infer_relation(sentence)
            for i in range(len(labels) - 1):
                edges.add((labels[i], labels[i + 1], rel))

    graph = {
        "meta": {
            "source": "중앙일보 RSS",
            "rss_url": rss_url,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "article": {
                "title": article.title,
                "link": article.link,
                "pub_date": article.pub_date,
            },
        },
        "nodes": sorted(nodes.values(), key=lambda n: n["label"]),
        "edges": [
            {"source": src, "target": dst, "relation": rel}
            for src, dst, rel in sorted(edges, key=lambda e: (e[0], e[1], e[2]))
        ],
    }
    return graph


def run(output_path: str, article_index: int = 0, article_count: int = 3) -> None:
    selected_rss, latest_items = load_latest_articles_from_rss(limit=article_count)
    if article_index < 0 or article_index >= len(latest_items):
        raise ValueError(f"article_index는 0~{len(latest_items)-1} 사이여야 합니다.")
    item = latest_items[article_index]

    article_html = fetch_text(item["link"])
    content = extract_article_text(article_html)
    article = Article(
        title=item["title"],
        link=item["link"],
        pub_date=item["pub_date"],
        summary=item["summary"],
        content=content,
    )

    graph = build_graph(article, selected_rss)
    graph["meta"]["article_candidates"] = [
        {
            "index": idx,
            "title": candidate["title"],
            "link": candidate["link"],
            "pub_date": candidate["pub_date"],
        }
        for idx, candidate in enumerate(latest_items)
    ]
    graph["meta"]["article_selected_index"] = article_index
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print(f"지식그래프 생성 완료: {output_path}")
    print(f"기사 제목: {article.title}")
    print(f"선택 인덱스: {article_index}")
    print(f"사용 RSS: {selected_rss}")
    print(f"노드 수: {len(graph['nodes'])}, 엣지 수: {len(graph['edges'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="중앙일보 RSS 지식그래프 생성기")
    parser.add_argument(
        "--output",
        default="backend/output/news1_kg.json",
        help="지식그래프 JSON 파일 경로",
    )
    parser.add_argument(
        "--article-index",
        type=int,
        default=0,
        help="최신 기사 목록에서 선택할 인덱스(0부터 시작)",
    )
    parser.add_argument(
        "--article-count",
        type=int,
        default=3,
        help="RSS에서 가져올 최신 기사 개수",
    )
    args = parser.parse_args()
    run(args.output, article_index=args.article_index, article_count=args.article_count)
