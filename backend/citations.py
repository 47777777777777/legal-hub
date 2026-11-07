"""
backend/citations.py

條文引用解析與結構化連結模組（符合 Prompt 4E 第 2 項與 Prompt 4G 第 1 項規範）。
實作四大核心規則：
1. explicit（顯式引用）：包含法規名稱之引用（例：「民法第 184 條」），解析至對應法規。
2. chain（連鎖引用）：「同法第 N 條」，連鎖至同條文中前一個顯式引用之法規。
3. host（宿主引用）：「本法第 N 條」或單純「第 N 條」，解析至當前法規（host_act_id）。
4. unresolved（未解析）：法規不存在於資料庫，或條號不在範圍內。
"""

import os
import re
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "legal_hub.db"
CONFIG_SLUGS = BASE_DIR / "config" / "slugs.json"

CHN_DIGITS = {
    '零': 0, '〇': 0, '一': 1, '二': 2, '兩': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9
}

COMMON_ALIASES = {
    "刑法": "中華民國刑法",
    "憲法": "中華民國憲法",
    "民訴": "民事訴訟法",
    "民訴法": "民事訴訟法",
    "刑訴": "刑事訴訟法",
    "刑訴法": "刑事訴訟法",
    "行訴": "行政訴訟法",
    "行訴法": "行政訴訟法",
    "勞基法": "勞動基準法",
    "保險法": "保險法",
    "國賠法": "國家賠償法",
    "消保法": "消費者保護法",
    "社維法": "社會秩序維護法",
    "個資法": "個人資料保護法",
    "採購法": "政府採購法",
    "證交法": "證券交易法",
    "智財法": "智慧財產案件審理法",
    "商標法": "商標法",
    "專利法": "專利法",
    "著作權法": "著作權法",
    "營業秘密法": "營業秘密法",
}

def chn_to_int(chn_str: str) -> Optional[int]:
    """將中文數字字串（例：一百二十三、二十）轉為整數"""
    if not chn_str:
        return None
    chn_str = chn_str.strip()
    if chn_str.isdigit():
        return int(chn_str)
    
    val = 0
    temp = 0
    for char in chn_str:
        if char in CHN_DIGITS:
            temp = CHN_DIGITS[char]
        elif char == '十':
            if temp == 0:
                temp = 1
            val += temp * 10
            temp = 0
        elif char == '百':
            val += temp * 100
            temp = 0
        elif char == '千':
            val += temp * 1000
            temp = 0
    val += temp
    return val

def normalize_article_no(raw_no: Optional[str]) -> str:
    """
    標準化條號為資料庫格式：
    '一百八十四' -> '184'
    '第一百八十五條之三' -> '185-3'
    '第 185 條之 3' -> '185-3'
    '185-3' -> '185-3'
    '185之3' -> '185-3'
    """
    if not raw_no:
        return ""
    raw = raw_no.strip()
    if raw.startswith("第"):
        raw = raw[1:].strip()
    if raw.endswith("條"):
        raw = raw[:-1].strip()
        
    sub_match = re.search(r'([零〇一二三四五六七八九十百千0-9]+)\s*(?:條之|之|-)\s*([零〇一二三四五六七八九十百千0-9]+)', raw)
    if sub_match:
        main_part = sub_match.group(1)
        sub_part = sub_match.group(2)
        main_int = chn_to_int(main_part)
        sub_int = chn_to_int(sub_part)
        return f"{main_int}-{sub_int}"
    
    num_int = chn_to_int(raw)
    if num_int is not None:
        return str(num_int)
    return raw

# 快取全庫法規名稱、別名、與快速查找集合
_ACT_LOOKUP: Optional[Dict[str, Dict[str, str]]] = None
_KNOWN_ACT_NAMES: Optional[Set[str]] = None
_MAX_NAME_LEN: int = 35

def get_act_lookup(db_path: str = "") -> Tuple[Dict[str, Dict[str, str]], Set[str]]:
    global _ACT_LOOKUP, _KNOWN_ACT_NAMES, _MAX_NAME_LEN
    if _ACT_LOOKUP is not None and _KNOWN_ACT_NAMES is not None:
        return _ACT_LOOKUP, _KNOWN_ACT_NAMES
    
    lookup = {}
    actual_db = db_path or str(DB_PATH)
    if os.path.exists(actual_db):
        try:
            conn = sqlite3.connect(actual_db)
            cur = conn.cursor()
            cur.execute("SELECT id, pcode, name FROM acts")
            rows = cur.fetchall()
            for act_id, pcode, name in rows:
                info = {"id": act_id, "pcode": pcode, "name": name}
                lookup[name] = info
                if pcode:
                    lookup[pcode.lower()] = info
                    lookup[pcode.upper()] = info
                if act_id:
                    lookup[act_id] = info
            conn.close()
        except Exception:
            pass

    # 讀取 config/slugs.json
    if CONFIG_SLUGS.exists():
        try:
            with open(CONFIG_SLUGS, "r", encoding="utf-8") as f:
                slugs = json.load(f)
                for name, slug in slugs.items():
                    if name in lookup:
                        lookup[name]["slug"] = slug
                        lookup[slug] = lookup[name]
                    else:
                        info = {"id": slug, "pcode": "", "name": name, "slug": slug}
                        lookup[name] = info
                        lookup[slug] = info
        except Exception:
            pass
            
    # 加入常見別名
    for alias, target_name in COMMON_ALIASES.items():
        if target_name in lookup:
            lookup[alias] = lookup[target_name]

    known_names = set(k for k in lookup.keys() if len(k) >= 2 and not k.startswith("http"))
    _MAX_NAME_LEN = max((len(k) for k in known_names), default=35)
    _KNOWN_ACT_NAMES = known_names
    _ACT_LOOKUP = lookup
    return _ACT_LOOKUP, _KNOWN_ACT_NAMES


ART_PATTERN = r'(?:(?:第\s*)?[0-9０-９零〇一二三四五六七八九十百千]+(?:\s*條之\s*|\s*條\s*之\s*|\s*之\s*|\s*-\s*)[0-9０-９零〇一二三四五六七八九十百千]+(?:\s*條)?|(?:第\s*)?[0-9０-９零〇一二三四五六七八九十百千]+\s*條)'

# 核心條文引用匹配正規式
# 匹配格式：
# [同法/本法]? <條號表達式> (至 <條號表達式>)?
RE_ARTICLE_REF = re.compile(
    rf'(?:(同法|本法)\s*)?'
    rf'({ART_PATTERN})'
    rf'(?:\s*至\s*({ART_PATTERN}))?'
)

def resolve_citations(
    text: str,
    host_act_id: str = "",
    host_act_name: str = "",
    db_path: str = ""
) -> List[Dict[str, Any]]:
    """
    解析條文內的所有法條引用，並回傳結構化引用清單。
    """
    if not text:
        return []
        
    act_lookup, known_names = get_act_lookup(db_path)
    
    # 宿主法規資訊解析
    host_info = None
    if host_act_id and host_act_id in act_lookup:
        host_info = act_lookup[host_act_id]
    elif host_act_name and host_act_name in act_lookup:
        host_info = act_lookup[host_act_name]
    
    if not host_act_name and host_info:
        host_act_name = host_info.get("name", "")
    if not host_act_id and host_info:
        host_act_id = host_info.get("id", "")
        
    citations = []
    last_explicit_act_info = None
    
    pos = 0
    while pos < len(text):
        # 檢查當前位置是否為顯式法規名開頭（最長匹配）
        act_text = None
        match_end = pos
        max_l = min(_MAX_NAME_LEN, len(text) - pos)
        for l in range(max_l, 1, -1):
            sub = text[pos:pos+l]
            if sub in known_names:
                act_text = sub
                match_end = pos + l
                break

        explicit_act_info = act_lookup.get(act_text) if act_text else None
        current_start = pos
        
        if explicit_act_info:
            
            # 跳過法規名與條號之間的空白或贅字 (如「規定之」)
            skip_match = re.match(r'\s*', text[match_end:])
            check_art_pos = match_end + (skip_match.end() if skip_match else 0)
            
            art_match = RE_ARTICLE_REF.match(text, check_art_pos)
            if art_match:
                # 成功匹配顯式法規引用！例：「民法第 184 條」
                pronoun = art_match.group(1)
                start_raw = art_match.group(2)
                end_raw = art_match.group(3)
                full_end = art_match.end()
                full_text = text[current_start:full_end]
                
                norm_start = normalize_article_no(start_raw)
                ref_articles = [norm_start]
                if end_raw:
                    norm_end = normalize_article_no(end_raw)
                    try:
                        s_int = int(norm_start)
                        e_int = int(norm_end)
                        if s_int <= e_int and (e_int - s_int) <= 50:
                            ref_articles = [str(i) for i in range(s_int, e_int + 1)]
                        else:
                            ref_articles = [norm_start, norm_end]
                    except ValueError:
                        ref_articles = [norm_start, norm_end]
                        
                target_id = explicit_act_info.get("slug") or explicit_act_info.get("id") or explicit_act_info.get("pcode")
                target_name = explicit_act_info.get("name", act_text)
                last_explicit_act_info = explicit_act_info
                
                citations.append({
                    "ref_text": full_text,
                    "ref_type": "explicit",
                    "ref_act_id": target_id,
                    "ref_act_name": target_name,
                    "ref_article_no": norm_start,
                    "ref_articles": ref_articles,
                    "start_pos": current_start,
                    "end_pos": full_end
                })
                pos = full_end
                continue
                
        # 檢查非顯式引用 (本法、同法、或直接第 N 條)
        art_match = RE_ARTICLE_REF.match(text, pos)
        if art_match:
            pronoun = art_match.group(1)
            start_raw = art_match.group(2)
            end_raw = art_match.group(3)
            full_end = art_match.end()
            full_text = text[pos:full_end]
            
            norm_start = normalize_article_no(start_raw)
            ref_articles = [norm_start]
            if end_raw:
                norm_end = normalize_article_no(end_raw)
                try:
                    s_int = int(norm_start)
                    e_int = int(norm_end)
                    if s_int <= e_int and (e_int - s_int) <= 50:
                        ref_articles = [str(i) for i in range(s_int, e_int + 1)]
                    else:
                        ref_articles = [norm_start, norm_end]
                except ValueError:
                    ref_articles = [norm_start, norm_end]
                    
            if pronoun == "同法":
                ref_type = "chain"
                target_info = last_explicit_act_info or host_info
            elif pronoun == "本法":
                ref_type = "host"
                target_info = host_info
            else:
                ref_type = "host"
                target_info = host_info
                
            target_id = ""
            target_name = ""
            if target_info:
                target_id = target_info.get("slug") or target_info.get("id") or target_info.get("pcode") or ""
                target_name = target_info.get("name", "")
                
            citations.append({
                "ref_text": full_text,
                "ref_type": ref_type,
                "ref_act_id": target_id,
                "ref_act_name": target_name,
                "ref_article_no": norm_start,
                "ref_articles": ref_articles,
                "start_pos": pos,
                "end_pos": full_end
            })
            pos = full_end
            continue
            
        pos += 1
        
    return citations


def init_text_refs_table(conn: sqlite3.Connection):
    """建立 text_refs 資料表與索引"""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS text_refs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_id TEXT NOT NULL,
            article_no TEXT NOT NULL,
            ref_act_id TEXT,
            ref_article_no TEXT,
            ref_text TEXT NOT NULL,
            ref_type TEXT NOT NULL,
            start_pos INTEGER NOT NULL,
            end_pos INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_text_refs_source ON text_refs(act_id, article_no)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_text_refs_target ON text_refs(ref_act_id, ref_article_no)")
    conn.commit()
