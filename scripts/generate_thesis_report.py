from __future__ import annotations

import html
import json
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "Bao_cao_luan_an_day_du_he_thong_giam_sat_tin_tuc.docx"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
}


def read_json(path: Path, default):
    try:
        if not path.is_file():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def run(text: str, *, bold=False, italic=False, size=None, color=None) -> str:
    props = []
    if bold:
        props.append("<w:b/>")
    if italic:
        props.append("<w:i/>")
    if size:
        props.append(f'<w:sz w:val="{int(size)}"/>')
    if color:
        props.append(f'<w:color w:val="{color}"/>')
    rpr = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    parts = []
    for i, line in enumerate(str(text).split("\n")):
        if i:
            parts.append("<w:br/>")
        parts.append(f'<w:t xml:space="preserve">{esc(line)}</w:t>')
    return f"<w:r>{rpr}{''.join(parts)}</w:r>"


def para(text="", *, style=None, align=None, runs=None, after=150, before=None) -> str:
    ppr = []
    if style:
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if align:
        ppr.append(f'<w:jc w:val="{align}"/>')
    spacing = []
    if before is not None:
        spacing.append(f'w:before="{before}"')
    if after is not None:
        spacing.append(f'w:after="{after}"')
    if spacing:
        ppr.append(f"<w:spacing {' '.join(spacing)}/>")
    ppr_xml = f"<w:pPr>{''.join(ppr)}</w:pPr>" if ppr else ""
    body = "".join(runs) if runs is not None else run(text)
    return f"<w:p>{ppr_xml}{body}</w:p>"


def heading(text: str, level=1) -> str:
    return para(text, style=f"Heading{level}", before=320 if level == 1 else 200, after=150)


def bullet(text: str) -> str:
    return para("", style="ListParagraph", runs=[run("• ", bold=True), run(text)], after=70)


def numbered(index: int, text: str) -> str:
    return para("", style="ListParagraph", runs=[run(f"{index}. ", bold=True), run(text)], after=80)


def page_break() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def table_cell(text: object, *, bold=False) -> str:
    return (
        "<w:tc><w:tcPr><w:tcW w:w=\"0\" w:type=\"auto\"/>"
        "<w:tcMar><w:top w:w=\"80\" w:type=\"dxa\"/><w:left w:w=\"80\" w:type=\"dxa\"/>"
        "<w:bottom w:w=\"80\" w:type=\"dxa\"/><w:right w:w=\"80\" w:type=\"dxa\"/></w:tcMar>"
        f"</w:tcPr>{para(str(text), runs=[run(str(text), bold=bold)], after=80)}</w:tc>"
    )


def table(rows: list[list[object]], *, header=True) -> str:
    out = [
        '<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/>'
        '<w:tblW w:w="0" w:type="auto"/><w:tblLook w:val="04A0"/></w:tblPr>'
    ]
    for row_index, row in enumerate(rows):
        out.append("<w:tr>")
        for value in row:
            out.append(table_cell(value, bold=header and row_index == 0))
        out.append("</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)


def png_size(path: Path):
    data = path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    return 1200, 800


def image(path: Path, rid="rIdImage1", width_in=6.2) -> str:
    if not path.exists():
        return para("Không tìm thấy hình sơ đồ hệ thống.", runs=[run("Không tìm thấy hình sơ đồ hệ thống.", italic=True)])
    width, height = png_size(path)
    cx = int(width_in * 914400)
    cy = int(cx * height / max(width, 1))
    return f"""
<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:drawing>
<wp:inline distT="0" distB="0" distL="0" distR="0">
<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>
<wp:docPr id="1" name="Sơ đồ hệ thống"/><wp:cNvGraphicFramePr/>
<a:graphic xmlns:a="{NS['a']}"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
<pic:pic xmlns:pic="{NS['pic']}"><pic:nvPicPr><pic:cNvPr id="0" name="so_do_he_thong.png"/><pic:cNvPicPr/></pic:nvPicPr>
<pic:blipFill><a:blip r:embed="{rid}" xmlns:r="{NS['r']}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
</pic:pic></a:graphicData></a:graphic>
</wp:inline></w:drawing></w:r></w:p>
"""


def add_bullets(body: list[str], items: list[str]) -> None:
    for item in items:
        body.append(bullet(item))


def build_document() -> tuple[str, bool]:
    config = read_json(ROOT / "config" / "config.json", {})
    google_news = config.get("google_news") if isinstance(config.get("google_news"), dict) else {}
    targets = config.get("targets") if isinstance(config.get("targets"), list) else []
    press = read_json(ROOT / "config" / "Chinh_thong.json", [])
    notifs = read_json(ROOT / "data" / "notifications.json", {})
    history = read_json(ROOT / "data" / "history.json", [])

    channel_hd = len(notifs.get("channel_hoatdong") or []) if isinstance(notifs, dict) else 0
    channel_bd = len(notifs.get("channel_biendong") or []) if isinstance(notifs, dict) else 0
    press_count = len(press) if isinstance(press, list) else 0
    history_count = len(history) if isinstance(history, list) else 0
    today = datetime.now().strftime("%d/%m/%Y")

    body: list[str] = []

    body.extend(
        [
            para("BÁO CÁO LUẬN ÁN", style="Title", align="center", after=260),
            para(
                "XÂY DỰNG HỆ THỐNG GIÁM SÁT TIN TỨC VỀ HOẠT ĐỘNG VÀ BIẾN ĐỘNG CHỨC VỤ CỦA ĐỐI TƯỢNG LÃNH ĐẠO",
                style="Subtitle",
                align="center",
                after=360,
            ),
            para("", after=520),
            para("Tên chương trình: followDirectorActivities", align="center"),
            para("Điểm khởi chạy: He_thong.py", align="center"),
            para("Nền tảng triển khai: Python Flask, Google News, RSS, Gemini AI, Telegram Bot API", align="center"),
            para(f"Ngày lập báo cáo: {today}", align="center"),
            para("", after=900),
            para(
                "Báo cáo được biên soạn hoàn toàn bằng tiếng Việt, dựa trên mã nguồn, cấu hình và dữ liệu hiện có trong dự án.",
                align="center",
                runs=[run("Báo cáo được biên soạn hoàn toàn bằng tiếng Việt, dựa trên mã nguồn, cấu hình và dữ liệu hiện có trong dự án.", italic=True)],
            ),
            page_break(),
        ]
    )

    body.extend(
        [
            heading("LỜI MỞ ĐẦU", 1),
            para(
                "Trong thời đại thông tin số, tin tức về hoạt động của lãnh đạo, cơ quan quản lý và nhân vật công chúng được cập nhật liên tục trên nhiều báo điện tử, cổng thông tin và nền tảng tổng hợp tin. Việc theo dõi thủ công từng đối tượng đòi hỏi nhiều thời gian, dễ bỏ sót tin quan trọng và khó phân biệt giữa bài viết thật sự liên quan với bài chỉ nhắc tên hoặc nhắc chức danh một cách gián tiếp."
            ),
            para(
                "Đề tài này tập trung xây dựng một hệ thống giám sát tin tức tự động, có khả năng thu thập, phân tích, phân loại và hiển thị kết quả theo từng đối tượng. Điểm nổi bật của hệ thống là kết hợp giữa tìm kiếm tin tức, lọc nguồn báo, phân tích bằng trí tuệ nhân tạo và giao diện dashboard để hỗ trợ người vận hành đưa ra đánh giá nhanh."
            ),
            para(
                "Báo cáo trình bày đầy đủ cơ sở hình thành đề tài, mục tiêu, yêu cầu, thiết kế kiến trúc, thiết kế dữ liệu, quy trình xử lý, chức năng giao diện, bảo mật, kiểm thử, đánh giá kết quả và định hướng phát triển của chương trình."
            ),
            page_break(),
            heading("TÓM TẮT BÁO CÁO", 1),
            para(
                "Chương trình followDirectorActivities là một ứng dụng web chạy cục bộ, cho phép người dùng quản lý danh sách đối tượng cần theo dõi, cấu hình cách tìm kiếm tin tức, lựa chọn chế độ phân tích AI, thực hiện quét thủ công hoặc quét nền tự động, xem kết quả trên dashboard và nhận thông báo qua Telegram."
            ),
            para(
                "Hệ thống sử dụng Google News và RSS để thu thập tin, sau đó dùng Gemini AI để đánh giá các tiêu chí nghiệp vụ: bài viết có đúng đối tượng không, đối tượng có sự tham gia hoặc hoạt động trong bài không, và bài viết có phản ánh biến động chức vụ không. Kết quả được lưu thành hai nhóm dữ liệu chính là tin hoạt động và tin biến động chức vụ."
            ),
            table(
                [
                    ["Chỉ tiêu", "Giá trị hiện tại"],
                    ["Số đối tượng đang cấu hình", len(targets)],
                    ["Số nguồn báo chính thống", press_count],
                    ["Chế độ AI hiện tại", google_news.get("ai_scan_mode", "")],
                    ["Cách tìm kiếm hiện tại", google_news.get("search_match_mode", "")],
                    ["Số tin tối đa cho mỗi đối tượng", google_news.get("max_results_per_target", "")],
                    ["Số tin hoạt động đã lưu", channel_hd],
                    ["Số tin biến động chức vụ đã lưu", channel_bd],
                    ["Số URL trong lịch sử xử lý", history_count],
                ]
            ),
            page_break(),
            heading("MỤC LỤC KHÁI QUÁT", 1),
        ]
    )

    for index, title in enumerate(
        [
            "Tổng quan đề tài",
            "Cơ sở lý thuyết và công nghệ sử dụng",
            "Khảo sát và phân tích yêu cầu",
            "Thiết kế kiến trúc hệ thống",
            "Thiết kế dữ liệu",
            "Thiết kế thuật toán và luồng xử lý",
            "Triển khai các chức năng chính",
            "Thiết kế giao diện người dùng",
            "Bảo mật và vận hành",
            "Kiểm thử và đánh giá",
            "Hạn chế và hướng phát triển",
            "Kết luận",
            "Phụ lục",
        ],
        1,
    ):
        body.append(numbered(index, title))
    body.append(page_break())

    chapters = [
        (
            "CHƯƠNG 1. TỔNG QUAN ĐỀ TÀI",
            [
                ("1.1. Lý do chọn đề tài", [
                    "Hoạt động của lãnh đạo và biến động chức vụ là nhóm thông tin có giá trị theo dõi cao trong nhiều bối cảnh như tổng hợp báo cáo, truyền thông, hành chính, nghiên cứu tổ chức, theo dõi chính sách và quản trị thông tin.",
                    "Một bài báo có thể chỉ nhắc tên đối tượng trong phần bối cảnh nhưng nội dung chính lại nói về cơ quan, địa phương hoặc một cá nhân khác. Nếu chỉ dùng tìm kiếm từ khóa, hệ thống dễ thu về nhiều tin nhiễu. Vì vậy, đề tài cần một cơ chế phân tích ngữ nghĩa để xác định bài viết có thật sự liên quan hay không.",
                ]),
                ("1.2. Mục tiêu nghiên cứu", [
                    "Tự động hóa quy trình tìm kiếm và tổng hợp tin tức theo từng đối tượng.",
                    "Giảm tin nhiễu bằng cách sử dụng AI để kiểm tra đúng đối tượng và sự tham gia của đối tượng trong bài viết.",
                    "Phát hiện các bài viết có dấu hiệu thay đổi chức vụ như bổ nhiệm, miễn nhiệm, điều động hoặc phân công nhiệm vụ.",
                    "Cung cấp giao diện trực quan để người dùng theo dõi, lọc, đánh dấu và xuất dữ liệu.",
                    "Hỗ trợ vận hành liên tục thông qua quét nền và thông báo Telegram.",
                ]),
                ("1.3. Phạm vi nghiên cứu", [
                    "Đối tượng nghiên cứu của hệ thống là các tin bài công khai trên Internet liên quan đến danh sách cá nhân được cấu hình. Phạm vi thu thập tập trung vào Google News và RSS của các nguồn báo được khai báo trong danh sách báo chính thống. Hệ thống không thay thế kết luận kiểm chứng của con người mà đóng vai trò công cụ hỗ trợ theo dõi và tổng hợp.",
                ]),
            ],
        ),
        (
            "CHƯƠNG 2. CƠ SỞ LÝ THUYẾT VÀ CÔNG NGHỆ SỬ DỤNG",
            [
                ("2.1. Tổng hợp tin tức tự động", [
                    "Tổng hợp tin tức tự động là quá trình lấy dữ liệu từ nhiều nguồn, chuẩn hóa thông tin, loại bỏ trùng lặp và trình bày kết quả theo một cấu trúc thống nhất. Trong chương trình này, dữ liệu tin gồm tiêu đề, mô tả, URL, nguồn báo, ngày đăng, đối tượng liên quan và kết quả phân tích AI.",
                ]),
                ("2.2. Google News và RSS", [
                    "Google News có ưu điểm là phạm vi bao phủ rộng và hỗ trợ truy vấn theo từ khóa. RSS có ưu điểm là truy cập trực tiếp từ nguồn báo, ít phụ thuộc vào decode URL và thường nhanh hơn. Việc kết hợp hai nguồn giúp hệ thống vừa có độ phủ, vừa có độ ổn định khi lọc nguồn báo chính thống.",
                ]),
                ("2.3. Phân tích bằng mô hình ngôn ngữ lớn", [
                    "Gemini AI được sử dụng để đọc tiêu đề, mô tả và ngữ cảnh đối tượng, sau đó trả về kết quả JSON. Việc yêu cầu AI trả JSON giúp hệ thống biến nhận định ngôn ngữ tự nhiên thành dữ liệu có cấu trúc để xử lý bằng chương trình.",
                ]),
            ],
        ),
        (
            "CHƯƠNG 3. KHẢO SÁT VÀ PHÂN TÍCH YÊU CẦU",
            [
                ("3.1. Bài toán nghiệp vụ", [
                    "Người vận hành cần biết trong một khoảng thời gian nhất định, mỗi đối tượng có hoạt động gì mới, có bài báo nào phản ánh sự thay đổi chức vụ hay không, và bài viết đó có thật sự liên quan đến đối tượng hay chỉ nhắc tên một cách gián tiếp.",
                ]),
                ("3.2. Yêu cầu chức năng", [
                    "Quản lý danh sách đối tượng với tên, chức vụ và tiểu sử.",
                    "Cấu hình nguồn báo chính thống và RSS tương ứng.",
                    "Chọn chế độ tìm kiếm Google News theo tên hoặc chức vụ, có hoặc không có ngoặc kép.",
                    "Chọn chế độ AI tùy mục tiêu: từ khóa, có sự tham gia, hoạt động, đầy đủ biến động chức vụ.",
                    "Quét toàn bộ, quét riêng từng đối tượng hoặc quét một nhóm đối tượng được chọn.",
                    "Tự quét nền theo chu kỳ cấu hình.",
                    "Xem chi tiết tin liên quan, tin không liên quan và tin biến động chức vụ của từng đối tượng.",
                    "Đánh dấu bài không liên quan, xuất dữ liệu JSON và gửi báo cáo Telegram.",
                ]),
                ("3.3. Yêu cầu phi chức năng", [
                    "Dễ sử dụng, giao diện có trạng thái rõ ràng.",
                    "Ổn định, tránh chạy nhiều lượt quét cùng lúc bằng khóa trong AutoScanner.",
                    "An toàn dữ liệu, ghi JSON theo cơ chế file tạm và thay thế nguyên tử.",
                    "Bảo mật, không đưa API key hoặc token Telegram vào giao diện hoặc file chia sẻ.",
                    "Dễ bảo trì, mã nguồn chia thành nhiều module theo nhiệm vụ.",
                ]),
            ],
        ),
        (
            "CHƯƠNG 4. THIẾT KẾ KIẾN TRÚC HỆ THỐNG",
            [
                ("4.1. Kiến trúc tổng thể", [
                    "Hệ thống được thiết kế theo mô hình ứng dụng web chạy cục bộ. Phần backend Flask chịu trách nhiệm cung cấp API, render template, gọi các module xử lý và quản lý trạng thái. Phần frontend sử dụng JavaScript thuần để gọi API, hiển thị thẻ kết quả và điều khiển modal cài đặt. Lõi nghiệp vụ nằm trong module monitor.py và auto_scanner.py.",
                ]),
                ("4.2. Phân rã module", [
                    "He_thong.py khởi động ứng dụng, cấu hình UTF-8, migrate file legacy và chạy Flask.",
                    "src/web.py định nghĩa route, API, xử lý request/response và render giao diện.",
                    "src/monitor.py thu thập tin, gọi Gemini, hậu kiểm AI và lưu notifications/history.",
                    "src/auto_scanner.py quản lý quét nền, khóa chống quét chồng và trạng thái hệ thống.",
                    "src/telegram_notify.py tạo digest Telegram, chống gửi trùng và chia tin dài.",
                    "src/secrets.py đọc .env, overlay secret runtime và che secret khi trả API.",
                ]),
            ],
        ),
    ]

    for chapter_title, sections in chapters:
        body.append(heading(chapter_title, 1))
        if chapter_title.startswith("CHƯƠNG 4"):
            body.append(image(ROOT / "docs" / "so_do_he_thong.png"))
            body.append(para("Hình 4.1. Sơ đồ tổng quan luồng hoạt động của hệ thống.", align="center", runs=[run("Hình 4.1. Sơ đồ tổng quan luồng hoạt động của hệ thống.", italic=True)]))
        for section_title, paragraphs in sections:
            body.append(heading(section_title, 2))
            for paragraph in paragraphs:
                if len(paragraph) < 180 and not paragraph.endswith("."):
                    body.append(bullet(paragraph))
                elif paragraph.startswith(("Quản lý", "Cấu hình", "Chọn", "Quét", "Tự", "Xem", "Đánh", "Dễ", "Ổn", "An", "Bảo", "He_thong", "src/")):
                    body.append(bullet(paragraph))
                else:
                    body.append(para(paragraph))
        body.append(page_break())

    body.extend(
        [
            heading("CHƯƠNG 5. THIẾT KẾ DỮ LIỆU", 1),
            heading("5.1. Nhóm file cấu hình", 2),
            para("File config/config.json lưu cấu hình vận hành nhưng không còn lưu secret thật. Các secret được chuyển sang .env. File config/Chinh_thong.json lưu danh sách báo chính thống, gồm tên báo, URL trang chủ và RSS nếu có."),
            table(
                [
                    ["File", "Nội dung"],
                    ["config/config.json", "Cấu hình AI, Google News, Telegram và danh sách đối tượng"],
                    ["config/Chinh_thong.json", "Danh sách nguồn báo chính thống"],
                    ["data/notifications.json", "Tin hoạt động và tin biến động chức vụ"],
                    ["data/history.json", "Khóa target|url đã xử lý"],
                    ["data/telegram_sent.json", "Khóa bài đã gửi Telegram"],
                    ["data/url_decode_cache.json", "Cache URL Google News đã decode"],
                ]
            ),
            heading("5.2. Cấu trúc bản ghi tin tức", 2),
            para("Mỗi bản ghi tin tức gồm các thông tin chính: timestamp, target_name, target_position, target_bio, title, description, url, resolved_url, published, press_name, press_domain, news_kind và ai_result. Trường ai_result là JSON do Gemini trả về và đã qua bước chuẩn hóa/hậu kiểm."),
            heading("5.3. Chống trùng dữ liệu", 2),
            para("Khóa chống trùng được thiết kế theo dạng tên đối tượng kết hợp URL. Cách này cho phép cùng một bài báo có thể được xét riêng cho nhiều đối tượng khác nhau, tránh trường hợp một URL xuất hiện với người A thì người B bị bỏ qua dù bài cũng có liên quan đến người B."),
            page_break(),
            heading("CHƯƠNG 6. THIẾT KẾ THUẬT TOÁN VÀ LUỒNG XỬ LÝ", 1),
            heading("6.1. Thuật toán quét một lượt", 2),
        ]
    )

    for i, item in enumerate(
        [
            "Đọc cấu hình runtime, bao gồm secret đã overlay từ .env.",
            "Đồng bộ chế độ AI từ ai_scan_mode sang các cờ nội bộ.",
            "Tạo danh sách đối tượng cần quét theo yêu cầu toàn bộ, một người hoặc nhiều người.",
            "Tạo truy vấn Google News theo search_match_mode.",
            "Thu thập bài viết từ Google News và RSS.",
            "Loại URL đã có trong history hoặc đã lưu, trừ khi ignore_history=true.",
            "Decode URL Google News song song và cập nhật cache.",
            "Lọc nguồn báo chính thống nếu người dùng bật.",
            "Gọi Gemini song song theo số worker cấu hình.",
            "Hậu kiểm kết quả AI, loại các bài không đạt điều kiện.",
            "Ghi dữ liệu vào notifications.json, cập nhật history.json.",
            "Gửi Telegram nếu cấu hình cho phép.",
        ],
        1,
    ):
        body.append(numbered(i, item))

    body.extend(
        [
            heading("6.2. Chế độ AI — có sự tham gia", 2),
            para("Đây là chế độ mới nhằm loại bỏ các bài báo không có sự tham gia của đối tượng. Prompt yêu cầu Gemini chỉ đặt Is_Activity=true khi đối tượng trực tiếp dự, chủ trì, phát biểu, làm việc, chỉ đạo, ký quyết định, được bổ nhiệm/miễn nhiệm hoặc là người chịu tác động chính của sự kiện. Các bài chỉ nhắc tên, dẫn bối cảnh, liệt kê chức danh, nói về cơ quan/người khác hoặc tiểu sử tĩnh sẽ bị loại khỏi danh sách lưu."),
            heading("6.3. Hậu kiểm kết quả Gemini", 2),
            para("Sau khi Gemini trả kết quả, hệ thống tiếp tục kiểm tra bằng các quy tắc bổ sung. Ví dụ: tin biến động chức vụ phải có từ khóa mạnh hoặc trường chức vụ/quyết định; nếu Matched_Target=false thì Is_Activity và Is_Change bị ép false; nếu tắt quét biến động chức vụ thì Is_Change bị loại khỏi kênh biến động."),
            page_break(),
            heading("CHƯƠNG 7. TRIỂN KHAI CÁC CHỨC NĂNG CHÍNH", 1),
        ]
    )

    feature_sections = [
        ("7.1. Quản lý đối tượng và tiểu sử", "Người dùng có thể thêm, sửa, xóa đối tượng trực tiếp trên dashboard. Mỗi đối tượng có tên, chức vụ và tiểu sử. Tiểu sử giúp AI nhận diện đối tượng trong các trường hợp bài báo chỉ ghi chức danh hoặc có nhiều người tên gần giống. Trên trang chi tiết, tiểu sử không hiển thị trực tiếp mà được mở bằng nút Tiểu sử để giữ giao diện gọn."),
        ("7.2. Quét thủ công và quét nền", "Quét thủ công được kích hoạt từ dashboard hoặc trang chi tiết. Quét nền do AutoScanner thực hiện theo chu kỳ. Cả hai cùng dùng chung lock để tránh chạy đồng thời. Khi đang quét, giao diện khóa các nút quét để tránh người dùng gửi thêm yêu cầu gây xung đột."),
        ("7.3. Quản lý tin không liên quan", "Trang chi tiết cho phép chọn nhiều bài và đánh dấu là không liên quan. Bài được gắn user_label=irrelevant sẽ chuyển sang tab Tin không liên quan. Người dùng vẫn có thể khôi phục nếu đánh dấu nhầm."),
        ("7.4. Xuất JSON", "Người dùng có thể xuất dữ liệu chi tiết của từng đối tượng trong cửa sổ thời gian hiện tại ra JSON. Tính năng này hỗ trợ lưu trữ, đối chiếu hoặc sử dụng dữ liệu cho báo cáo khác."),
        ("7.5. Telegram", "Khi bật Telegram, hệ thống gom tin mới theo đối tượng và gửi thành digest. Cơ chế chống trùng đảm bảo cùng một URL không bị gửi nhiều lần. Nếu nội dung dài, hệ thống chia thành nhiều tin để phù hợp giới hạn ký tự của Telegram."),
    ]
    for title, text in feature_sections:
        body.append(heading(title, 2))
        body.append(para(text))

    body.extend(
        [
            page_break(),
            heading("CHƯƠNG 8. THIẾT KẾ GIAO DIỆN NGƯỜI DÙNG", 1),
            heading("8.1. Dashboard", 2),
            para("Dashboard là màn hình vận hành chính. Thanh bên trái quản lý đối tượng và cài đặt. Khu vực trung tâm hiển thị các thẻ đối tượng, gồm tên, chức vụ, tiểu sử rút gọn, trạng thái và số lượng tin. Khu vực bên phải hiển thị trạng thái hệ thống, chu kỳ quét, lần quét cuối và tin mới nhất."),
            heading("8.2. Trang chi tiết đối tượng", 2),
            para("Trang chi tiết tập trung vào một đối tượng. Người dùng có thể xem thống kê tin, mở tiểu sử bằng nút riêng, xem tóm tắt, đọc danh sách hoạt động, đọc danh sách biến động chức vụ và quản lý các bài không liên quan. Cách tách tiểu sử ra nút riêng giúp trang không bị dài khi tiểu sử nhiều nội dung."),
            heading("8.3. Modal cài đặt", 2),
            para("Modal cài đặt gom các nhóm chức năng: phân tích và lọc, quét tự động, Telegram, danh sách báo chính thống và quản lý dữ liệu. Các lựa chọn được trình bày bằng thẻ, toggle, input số và nút hành động để người dùng thao tác nhanh."),
            page_break(),
            heading("CHƯƠNG 9. BẢO MẬT VÀ VẬN HÀNH", 1),
            heading("9.1. Quản lý secret", 2),
            para("Secret gồm Gemini API key, Telegram bot token và Telegram chat ID không được lưu trực tiếp trong config.json. Chúng được đặt trong file .env hoặc biến môi trường. Module src/secrets.py chịu trách nhiệm đọc .env, overlay secret vào cấu hình runtime và che secret khi trả config qua API."),
            heading("9.2. An toàn dữ liệu runtime", 2),
            para("File .gitignore đã loại trừ .env, config thật và data runtime khỏi phiên bản chia sẻ. Điều này giúp giảm nguy cơ đẩy nhầm token, key hoặc dữ liệu vận hành lên kho mã nguồn."),
            heading("9.3. Khuyến nghị triển khai", 2),
        ]
    )
    add_bullets(
        body,
        [
            "Nếu chỉ dùng cá nhân, nên chạy server ở localhost thay vì mở ra toàn mạng nội bộ.",
            "Nếu triển khai cho nhiều người dùng, cần bổ sung đăng nhập hoặc API token.",
            "Nên xoay API key và Telegram token nếu từng bị chia sẻ hoặc commit nhầm.",
            "Nên sao lưu config và data định kỳ nếu hệ thống được dùng lâu dài.",
        ],
    )

    body.extend(
        [
            page_break(),
            heading("CHƯƠNG 10. KIỂM THỬ VÀ ĐÁNH GIÁ", 1),
            heading("10.1. Kiểm thử đề xuất", 2),
            table(
                [
                    ["Nhóm kiểm thử", "Nội dung cần kiểm tra"],
                    ["Quản lý đối tượng", "Thêm, sửa, xóa tên/chức vụ/tiểu sử; kiểm tra config cập nhật đúng"],
                    ["Quét tin", "Quét toàn bộ, quét riêng, quét nhóm đối tượng"],
                    ["Chế độ AI", "So sánh keyword, participation, activity, full trên cùng một đối tượng"],
                    ["Lọc báo", "Bật/tắt báo chính thống và kiểm tra số tin thay đổi"],
                    ["Trang chi tiết", "Mở tiểu sử, đánh dấu không liên quan, khôi phục, tải JSON"],
                    ["Telegram", "Gửi thử, gửi digest, chống gửi trùng"],
                    ["Bảo mật", "Kiểm tra API không trả secret, config không chứa key/token"],
                ]
            ),
            heading("10.2. Đánh giá kết quả hiện tại", 2),
        ]
    )
    add_bullets(
        body,
        [
            "Hệ thống đã đáp ứng được mục tiêu giám sát tin tức theo danh sách đối tượng.",
            "Chế độ participation giúp giảm bài không liên quan do chỉ nhắc tên.",
            "Dashboard và trang chi tiết đã đủ chức năng cho vận hành cơ bản.",
            "Cơ chế chống trùng URL và Telegram sent giúp hạn chế lặp dữ liệu và spam thông báo.",
            "Bảo mật secret đã được cải thiện rõ rệt so với lưu trực tiếp trong config.",
        ],
    )
    body.append(heading("10.3. Hạn chế", 2))
    add_bullets(
        body,
        [
            "Dữ liệu JSON phù hợp quy mô nhỏ nhưng chưa tối ưu cho dữ liệu lớn.",
            "Kết quả AI phụ thuộc vào chất lượng prompt và quota dịch vụ Gemini.",
            "Chưa có hệ thống phân quyền người dùng.",
            "Chưa có bộ kiểm thử tự động đầy đủ cho toàn bộ nghiệp vụ.",
            "Google News có thể thay đổi kết quả theo thời gian nên khả năng tái lập tuyệt đối chưa cao.",
        ],
    )

    body.extend([page_break(), heading("CHƯƠNG 11. HƯỚNG PHÁT TRIỂN", 1)])
    add_bullets(
        body,
        [
            "Chuyển lưu trữ từ JSON sang SQLite để truy vấn nhanh, thống kê tốt và giảm rủi ro ghi file lớn.",
            "Bổ sung đăng nhập, phân quyền hoặc token truy cập cho các API nhạy cảm.",
            "Tạo bộ kiểm thử tự động bằng pytest cho backend và Playwright cho giao diện.",
            "Tạo báo cáo định kỳ tự động theo ngày, tuần, tháng và xuất Word/PDF.",
            "Chuẩn hóa tiểu sử đối tượng thành trường có cấu trúc: bí danh, chức vụ hiện tại, chức vụ cũ, tổ chức, địa phương.",
            "Thêm cơ chế học từ phản hồi người dùng: bài bị đánh dấu không liên quan có thể dùng để cải thiện prompt.",
            "Bổ sung dashboard thống kê theo nguồn báo, mức tin cậy AI và xu hướng hoạt động theo thời gian.",
        ],
    )

    body.extend(
        [
            page_break(),
            heading("KẾT LUẬN", 1),
            para("Hệ thống giám sát tin tức followDirectorActivities đã giải quyết được bài toán theo dõi hoạt động và biến động chức vụ của nhiều đối tượng trên nguồn tin công khai. Hệ thống kết hợp thu thập tin, lọc nguồn, phân tích bằng AI, lưu dữ liệu, hiển thị dashboard và gửi thông báo Telegram trong một quy trình tương đối hoàn chỉnh."),
            para("Về mặt kỹ thuật, chương trình có cấu trúc module rõ ràng, dễ bảo trì và đã được bổ sung nhiều chi tiết thực tế như chống trùng URL, cache decode, khóa quét nền, quản lý secret, tiểu sử đối tượng và chế độ AI lọc theo sự tham gia. Đây là nền tảng phù hợp để tiếp tục phát triển thành một công cụ vận hành ổn định hơn trong môi trường thực tế."),
            page_break(),
            heading("PHỤ LỤC A. DANH SÁCH API CHÍNH", 1),
            table(
                [
                    ["Phương thức", "Endpoint", "Chức năng"],
                    ["GET", "/", "Mở dashboard"],
                    ["GET", "/target", "Mở trang chi tiết đối tượng"],
                    ["GET", "/api/targets", "Lấy danh sách đối tượng"],
                    ["POST", "/config/targets/add", "Thêm hoặc sửa đối tượng"],
                    ["POST", "/config/targets/delete", "Xóa đối tượng"],
                    ["GET", "/api/settings", "Lấy cấu hình giao diện đã che secret"],
                    ["POST", "/api/settings", "Lưu cài đặt hệ thống"],
                    ["POST", "/monitor/run", "Bắt đầu quét"],
                    ["POST", "/monitor/cancel", "Hủy lượt quét đang chạy"],
                    ["GET", "/api/monitor/status", "Lấy trạng thái quét"],
                    ["GET", "/api/target/detail", "Chi tiết một đối tượng"],
                    ["GET", "/api/target/export.json", "Xuất dữ liệu JSON"],
                ]
            ),
            heading("PHỤ LỤC B. DANH SÁCH ĐỐI TƯỢNG HIỆN CÓ", 1),
        ]
    )
    rows = [["STT", "Họ tên", "Chức vụ", "Có tiểu sử"]]
    for index, target in enumerate(targets, 1):
        if isinstance(target, dict):
            rows.append(
                [
                    index,
                    target.get("name", ""),
                    target.get("position", ""),
                    "Có" if str(target.get("bio") or "").strip() else "Chưa",
                ]
            )
    body.append(table(rows))

    sect = (
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
        'w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'
    )
    document_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{NS["w"]}" xmlns:r="{NS["r"]}" xmlns:wp="{NS["wp"]}" '
        f'xmlns:a="{NS["a"]}" xmlns:pic="{NS["pic"]}"><w:body>{"".join(body)}{sect}</w:body></w:document>'
    )
    return document_xml, (ROOT / "docs" / "so_do_he_thong.png").exists()


def write_docx() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    document_xml, has_image = build_document()
    styles_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="{NS['w']}">
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:sz w:val="26"/></w:rPr><w:pPr><w:spacing w:line="276" w:lineRule="auto"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="38"/><w:color w:val="1F4E79"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="30"/><w:color w:val="1F4E79"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="32"/><w:color w:val="1F4E79"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="28"/><w:color w:val="2F5597"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="420"/></w:pPr></w:style>
<w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4" w:color="BFBFBF"/><w:left w:val="single" w:sz="4" w:color="BFBFBF"/><w:bottom w:val="single" w:sz="4" w:color="BFBFBF"/><w:right w:val="single" w:sz="4" w:color="BFBFBF"/><w:insideH w:val="single" w:sz="4" w:color="BFBFBF"/><w:insideV w:val="single" w:sz="4" w:color="BFBFBF"/></w:tblBorders></w:tblPr></w:style>
</w:styles>'''
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    doc_rels_items = [
        '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    ]
    if has_image:
        doc_rels_items.append(
            '<Relationship Id="rIdImage1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/so_do_he_thong.png"/>'
        )
    doc_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(doc_rels_items)
        + "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="png" ContentType="image/png"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        "</Types>"
    )
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document_xml)
        z.writestr("word/styles.xml", styles_xml)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        if has_image:
            z.write(ROOT / "docs" / "so_do_he_thong.png", "word/media/so_do_he_thong.png")


if __name__ == "__main__":
    write_docx()
    print(OUT.name)
    print(OUT.stat().st_size)
