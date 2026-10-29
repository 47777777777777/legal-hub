"""
Populates full legal corpus index and seed statutes into SQLite database
with exact LawPlayer fields from screenshots.
"""
import os
import sys
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.db import get_connection, DB_FILE, init_database

ACTS_DIR = os.path.join(BASE_DIR, "data", "acts")

ADDITIONAL_STATUTES = [
    {
        "id": "constitution",
        "name": "中華民國憲法",
        "name_en": "Constitution of the Republic of China",
        "last_modified": "民國 36 年 01 月 01 日",
        "category": "憲政 > 憲法目",
        "articles": [
            {
                "article_no": "1",
                "title": "國體",
                "content": "中華民國基於三民主義，為民有民治民享之民主共和國。",
                "summary": "確立中華民國之國體為民主共和國。"
            },
            {
                "article_no": "8",
                "title": "人身自由之保障",
                "content": "人民身體之自由應予保障。除現行犯之逮捕由法律另定外，非經司法或警察機關依法定程序，不得逮捕、拘禁。非由法院依法定程序，不得審問、處罰。非依法定程序之逮捕、拘禁、審問、處罰，得拒絕之。\n人民因犯罪嫌疑被逮捕拘禁時，其逮捕拘禁機關應將逮捕拘禁原因，以書面告知本人及其本人指定之親友，並至遲於二十四小時內移送該管法院審問。本人或他人亦得聲請該管法院，於二十四小時內向逮捕之機關提審。\n法院對於前項聲請，不得拒絕，並不得先令逮捕拘禁之機關查覆。逮捕拘禁之機關，對於法院之提審提票，不得拒絕或遲延。\n人民遭受任何機關非法逮捕拘禁時，其本人或他人得向法院聲請追究，法院不得拒絕，並應於二十四小時內向逮捕拘禁之機關追究，依法處理。",
                "summary": "憲法最核心之人權保障條款（人身自由與法院提審制度）。"
            },
            {
                "article_no": "22",
                "title": "概括基本權保障",
                "content": "凡人民之其他自由及權利，不妨害社會秩序公共利益者，均受憲法之保障。",
                "summary": "非列舉基本權之概括保障（如隱私權、人格權、性自主權）。"
            },
            {
                "article_no": "23",
                "title": "比例原則與法律保留",
                "content": "以上各條列舉之自由權利，除為防止妨礙他人自由、避免緊急危難、維持社會秩序，或增進公共利益所必要者外，不得以法律限制之。",
                "summary": "基本權限制之四大合憲要件：法律保留原則與比例原則（適當性、必要性、衡平性）。"
            }
        ]
    },
    {
        "id": "labor_standards_act",
        "name": "勞動基準法",
        "name_en": "Labor Standards Act",
        "last_modified": "民國 109 年 06 月 10 日",
        "category": "勞動 > 勞動條件目",
        "articles": [
            {
                "article_no": "1",
                "title": "立法目的與最低基準",
                "content": "為規定勞動條件最低標準，保障勞工權益，加強勞雇關係，促進社會與經濟發展，特制定本法；本法未規定者，適用其他法律之規定。\n雇主與勞工所訂勞動條件，不得低於本法所定之最低標準。",
                "summary": "勞動基準法之強制性與最低勞動條件保障原則。"
            },
            {
                "article_no": "11",
                "title": "經濟性解雇事由",
                "content": "非有左列情事之一者，雇主不得預告勞工終止勞動契約：\n一、歇業或轉讓時。\n二、虧損或業務緊縮時。\n三、不可抗力暫停工作在一個月以上時。\n四、業務性質變更，有減少勞工之必要，又無適當工作可供安置時。\n五、勞工對於所擔任之工作確不能勝任時。",
                "summary": "雇主發動資遣之五大法定限制事由，嚴格貫徹解雇最後手段性原則。"
            },
            {
                "article_no": "12",
                "title": "懲戒性解雇事由",
                "content": "勞工有左列情形之一者，雇主得不經預告終止契約：\n一、於訂立勞動契約時為虛偽意思表示，使雇主誤信而有受損害之虞者。\n二、對於雇主、雇主家屬、雇主代理人或其他共同工作之勞工，實施暴行或有重大侮辱之行為者。\n三、受有期徒刑以上刑之宣告確定，而未諭知緩刑或未准易科罰金者。\n四、違反勞動契約或工作規則，情節重大者。\n五、故意損耗機器、工具、原料、產品，或其他雇主所有物品，或故意洩漏雇主技術上、營業上之秘密，致雇主受有損害者。\n六、無正當理由繼續曠工三日，或一個月內曠工達六日者。\n雇主依前項第一款、第二款及第四款至第六款規定終止契約者，應自知悉其情形之日起，三十日內為之。",
                "summary": "開除（不經預告終止契約）之六大事由，第4款須達情節重大，除斥期間為三十日。"
            },
            {
                "article_no": "24",
                "title": "延長工時工資（加班費計算）",
                "content": "雇主延長勞工工作時間者，其延長工作時間之工資，依下列標準加給：\n一、延長工作時間在二小時以內者，按平日每小時工資額加給三分之一以上。\n二、再延長工作時間在二小時以內者，按平日每小時工資額加給三分之二以上。\n三、依第三十二條第四項之規定，延長工作時間者，按平日每小時工資額加倍發給。",
                "summary": "加班費之階梯式加乘法定標準（前2小時加1/3，後2小時加2/3）。"
            }
        ]
    },
    {
        "id": "admin_procedure_act",
        "name": "行政程序法",
        "name_en": "Administrative Procedure Act",
        "last_modified": "民國 110 年 04 月 28 日",
        "category": "行政 > 國家發展目",
        "articles": [
            {
                "article_no": "4",
                "title": "依法行政原則",
                "content": "行政行為應受法律及一般法律原則之拘束。",
                "summary": "行政法治之核心基石：消極依法行政（法律優位）與積極依法行政（法律保留）。"
            },
            {
                "article_no": "7",
                "title": "比例原則",
                "content": "行政行為，應依下列原則為之：\n一、採取之方法應有助於目的之達成。\n二、有多種同樣能達成目的之方法時，應選擇對人民權益損害最少者。\n三、採取之方法所造成之損害不得與欲達成目的之利益顯失均衡。",
                "summary": "比例原則三子原則：適當性、必要性（最小侵害）、衡平性。"
            },
            {
                "article_no": "92",
                "title": "行政處分之定義",
                "content": "本法所稱行政處分，係指行政機關就公法上具體事件所為之決定或其他公權力措施而對外直接發生法律效果之單方行政行為。\n前項決定或措施之相對人雖非特定，而依一般特徵可得確定其範圍者，為一般處分，適用本法關於行政處分之規定。有關公物之設定、變更、廢止或其一般使用者，亦同。",
                "summary": "行政處分之法定核心六大要件。"
            }
        ]
    },
    {
        "id": "company_act",
        "name": "公司法",
        "name_en": "Company Act",
        "last_modified": "民國 110 年 12 月 29 日",
        "category": "經濟 > 商業目",
        "articles": [
            {
                "article_no": "1",
                "title": "公司之定義",
                "content": "本法所稱公司，謂以營利為目的，依照本法組織、登記、成立之社團法人。",
                "summary": "公司之法人格與營利社團法人性質。"
            },
            {
                "article_no": "23",
                "title": "負責人之忠實與善良管理人注意義務",
                "content": "公司負責人應忠實執行業務並盡善良管理人之注意義務，如有違反致公司受有損害者，負損害賠償責任。\n公司負責人對於公司業務之執行，如有違反法令致他人受有損害時，對他人應與公司負連帶賠償之責。",
                "summary": "公司負責人受託義務（忠實與注意義務）。"
            }
        ]
    },
    {
        "id": "traffic_act",
        "name": "道路交通管理處罰條例",
        "name_en": "Road Traffic Management and Penalty Act",
        "last_modified": "民國 112 年 06 月 30 日",
        "category": "交通 > 公路目",
        "articles": [
            {
                "article_no": "35",
                "title": "酒駕與毒駕行政處罰",
                "content": "汽車駕駛人，駕駛汽車經測試檢定有下列情形之一，機車駕駛人處新臺幣一萬五千元以上九萬元以下罰鍰，汽車駕駛人處新臺幣三萬元以上十二萬元以下罰鍰，並均當場移置保管該汽機車及吊扣其駕駛執照一年至二年：\n一、酒精濃度超過規定標準。\n二、吸食毒品、迷幻藥、麻醉藥品及其相類之管制藥品。",
                "summary": "酒駕與毒駕行政罰鍰與吊扣駕照規定。"
            }
        ]
    }
]


def populate():
    init_database(DB_FILE)
    conn = get_connection(DB_FILE)
    cur = conn.cursor()

    cur.execute("DELETE FROM attachments")
    cur.execute("DELETE FROM article_enrichments")
    cur.execute("DELETE FROM articles")
    cur.execute("DELETE FROM acts")
    try:
        cur.execute("DELETE FROM articles_fts")
    except Exception:
        pass

    # 1. Load files from data/acts/*.json
    for fname in os.listdir(ACTS_DIR):
        if fname.endswith(".json"):
            fpath = os.path.join(ACTS_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                insert_act_data(cur, data, is_enriched=1)

    # 2. Insert additional seed statutes
    for act_data in ADDITIONAL_STATUTES:
        insert_act_data(cur, act_data, is_enriched=1)

    conn.commit()
    conn.close()
    print("Database populated with complete LawPlayer schema!")


def insert_act_data(cur, data: dict, is_enriched: int = 1):
    act_id = data.get("id")
    name = data.get("name")
    if not act_id or not name:
        return

    cur.execute("""
        INSERT OR REPLACE INTO acts (
            id, pcode, name, name_en, last_modified, category, 
            org_reform_notice, history_json, legislative_process_json, 
            chapters_json, attachments_json, is_enriched
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        act_id,
        data.get("pcode", act_id),
        name,
        data.get("name_en", ""),
        data.get("last_modified", ""),
        data.get("category", ""),
        data.get("org_reform_notice", ""),
        json.dumps(data.get("history", []), ensure_ascii=False),
        json.dumps(data.get("legislative_process", []), ensure_ascii=False),
        json.dumps(data.get("chapters", []), ensure_ascii=False),
        json.dumps(data.get("attachments", []), ensure_ascii=False),
        is_enriched
    ))

    # Insert attachments
    for att in data.get("attachments", []):
        cur.execute("""
            INSERT OR REPLACE INTO attachments (id, act_id, article_no, title, file_type, url, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            att.get("id", f"att_{abs(hash(att.get('url', '')))}"),
            act_id,
            att.get("related_article"),
            att.get("title", ""),
            att.get("file_type", "PDF"),
            att.get("url", ""),
            att.get("description", "")
        ))

    # Insert articles
    for art in data.get("articles", []):
        art_no = str(art.get("article_no")).strip()
        cur.execute("""
            INSERT OR REPLACE INTO articles (act_id, article_no, title, chapter, content)
            VALUES (?, ?, ?, ?, ?)
        """, (
            act_id,
            art_no,
            art.get("title", ""),
            art.get("chapter", ""),
            art.get("content", "")
        ))

        try:
            cur.execute("""
                INSERT INTO articles_fts (act_id, article_no, title, content)
                VALUES (?, ?, ?, ?)
            """, (act_id, art_no, art.get("title", ""), art.get("content", "")))
        except Exception:
            pass

        # Enrichments: store rich LawPlayer payload
        cur.execute("""
            INSERT OR REPLACE INTO article_enrichments (
                act_id, article_no, summary, reading_time, vernacular_qa_json,
                elements_json, key_issues_json, legislative_reasons,
                amendment_history_json, practical_insights_json, lawplayer_link,
                related_articles_json, attachments_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            act_id,
            art_no,
            art.get("summary", ""),
            art.get("reading_time", "3 分鐘"),
            json.dumps(art.get("vernacular_qa", []), ensure_ascii=False),
            json.dumps(art.get("elements", []), ensure_ascii=False),
            json.dumps(art.get("key_issues", []), ensure_ascii=False),
            art.get("legislative_reasons", ""),
            json.dumps(art.get("amendment_history", []), ensure_ascii=False),
            json.dumps(art.get("practical_insights", []), ensure_ascii=False),
            art.get("lawplayer_link", f"https://lawplayer.com/act/#article_{art_no}"),
            json.dumps(art.get("related_articles", []), ensure_ascii=False),
            json.dumps(art.get("attachments", []), ensure_ascii=False)
        ))


if __name__ == "__main__":
    populate()
