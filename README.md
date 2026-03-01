<div align="center">

🦭 SEAL InsightBox™

Hệ thống chống đứt gãy tri thức & Trợ lý học tập Đa luồng (Hybrid Edge-Cloud AI)

</div>

🚦 Tình trạng Dự án (Project Status)

Dự án đang trong giai đoạn phát triển tích cực (Active Development). Dưới đây là tiến độ các module:

[x] SealAI™ Router Core: Đã hoàn thiện. Xử lý định tuyến thông minh, Fallback Protocol và phân tải Edge-Cloud.

[x] Web Dashboard (Router UI): Đã hoàn thiện. Monitor realtime log, TTFT, và TPS.

[ ] Smart Edge Capture Node (Hardware): Đang phát triển (Tích hợp NPU, Camera, Mic Array trên board Orange Pi).

[ ] Frontend Student App: Đang phát triển (Tính năng Time-Sync Slider, hiển thị UI đa luồng).

[ ] Dual-Embedding & Vector DB: Đang tích hợp (Qdrant & BGE-M3).

🚀 Tính Năng Cốt Lõi (Key Features)

🧠 1. SealAI™ Smart Routing (LLM-based Router)

Hệ thống sử dụng Gemma 3 đóng vai trò làm "Trạm điều phối tư duy". Router sẽ phân tích độ phức tạp của câu hỏi (Cognitive Load) từ học sinh để định tuyến:

EASY (Truy xuất cơ bản): Xử lý tại chỗ (Local Edge Node) để bảo mật dữ liệu và tiết kiệm 100% chi phí API (Zero-cost).

MEDIUM (Tóm tắt, giải thích): Định tuyến tới Cloud (Gemini 2.5 Flash / Haiku).

HARD (Toán học, suy luận sâu): Kích hoạt OpenAI GPT-4o/GPT-5 với tham số reasoning_effort="high".

📶 2. Nút Biên Thông Minh (Smart Edge Node) - In Dev

Thiết bị phần cứng tại lớp học (InsightBox) tối ưu cực hạn băng thông:

Zero-Stream Vision: NPU chạy mô hình YOLOv8n quét Bounding Box giáo viên. Chỉ chụp hình (Keyframe) khi có nét phấn mới (SSIM) và giáo viên không che bảng.

Offline-First & UPS Mode: Lưu cache vào thẻ MicroSD khi rớt mạng; tích hợp mạch Buck + Pin Lithium kháng lỗi cúp cầu dao.

⏱️ 3. Time-Sync Slider (UX/UI) - In Dev

Trải nghiệm học tập đậm chất điện ảnh: Kết nối trực tiếp "Snapshot nét phấn trên bảng" với "Audio lời giảng". Học sinh có thể kéo thanh trượt thời gian để tái hiện chính xác ngữ cảnh của tiết học.

🛠️ Cài đặt & Chạy Module Router (Quick Start)

Hiện tại, bạn có thể chạy thử nghiệm module SealAI™ Router cục bộ.

1. Yêu cầu hệ thống

Python 3.10 trở lên

Môi trường hỗ trợ chạy FastAPI

2. Cài đặt môi trường

Clone repository và cài đặt các thư viện cần thiết:

git clone [https://github.com/TonyBucket/InsightBox.git](https://github.com/TonyBucket/InsightBox.git)
cd InsightBox/"SealAI Router"
pip install -r requirements.txt


3. Cấu hình (Configuration)

Lần đầu tiên chạy, hệ thống sẽ tự động sinh ra file config.yaml. Bạn có thể chỉnh sửa file này để điền API Keys cho Google (Gemini) và OpenAI, hoặc thiết lập endpoint cho Local LLM của bạn.

4. Khởi động Router

python router.py


API Endpoint: http://localhost:6767/v1/chat/completions

Live Dashboard (Enterprise UI): Truy cập trực tiếp http://localhost:6767 trên trình duyệt để theo dõi luồng định tuyến và metric hệ thống theo thời gian thực.

👨‍💻 Đội ngũ phát triển (Team SEAL)

Dự án được xây dựng và phát triển cho cuộc thi AI Young Guru 2026.

Đào Huỳnh Chí Thăng (Tony) - AI & Systems Engineer & Hardware & IoT Specialist (Founder)

Trần Đông Kha - AI & Systems Engineer

Nguyễn Ngọc Tuyền - Research & Data Ops & Designer

📜 Giấy phép (License)

Dự án này được phân phối dưới giấy phép MIT License. Xem chi tiết tại file LICENSE.
