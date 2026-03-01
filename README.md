# 🦭 SEAL InsightBox™ - Edge-Cloud Hybrid AI Infrastructure

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

**InsightBox** là hệ thống hạ tầng trí tuệ nhân tạo chuyên biệt nhằm giải quyết bài toán "đứt gãy tri thức" trong môi trường giáo dục. Dự án tích hợp các công nghệ tối tân về Edge Computing, Multimodal RAG và Self-Routing LLM để số hóa toàn bộ ngữ cảnh lớp học vật lý (physical classroom).

---

## 🚀 Tính Năng Cốt Lõi (Key Features)

### 🧠 1. SealAI™ Smart Routing
Hệ thống sử dụng một mô hình ngôn ngữ lớn (ở demo ) đóng vai trò làm "Trạm điều phối". Router sẽ phân tích độ phức tạp của câu hỏi (Cognitive Load) để định tuyến dữ liệu:
- **EASY:** Xử lý tại chỗ (Local Edge) bằng Gemma 3 để bảo mật dữ liệu và tiết kiệm 100% chi phí API.
- **MEDIUM:** Định tuyến tới Gemini 2.5 Flash để tối ưu tốc độ.
- **HARD:** Kích hoạt OpenAI GPT-4o với tham số `reasoning_effort="high"` cho các bài toán chuyên sâu.

### 📶 2. Smart Edge Capture Node (IoT)
Thiết bị phần cứng tại lớp học tích hợp NPU (0.8 TOPS) chạy thuật toán **YOLOv8n** để:
- Tự động nhận diện bảng giảng.
- Chỉ chụp hình (Keyframe) khi giáo viên không che bảng và có nét phấn mới (thuật toán SSIM).
- Hoạt động **Offline-First** với Local Cache trên thẻ MicroSD.

### ⏱️ 3. Time-Sync Slider (UX/UI)
Giao diện người dùng cho phép học sinh "quay ngược thời gian" để xem chính xác nét phấn và lời giảng của thầy cô tại thời điểm kiến thức được hình thành.

---

## 🏗️ Kiến Trúc Hệ Thống (System Architecture)



Hệ thống vận hành dựa trên đường ống dữ liệu (Data Pipeline) 4 bước:
1. **Capture:** Thu thập đa luồng (Audio/Visual) tại Edge.
2. **Digest:** Bóc băng (Qwen3-ASR) và Chuẩn hóa Toán học (Gemma 3) tại Local Server.
3. **Embed:** Nhúng Vector vào Qdrant DB.
4. **Route:** Điều phối truy vấn thông minh qua SealAI™ Router.

---

## 💻 Cài Đặt (Installation)

### Yêu cầu hệ thống:
- Python 3.10+
- Local LLM Server (llama.cpp hoặc Ollama)

### Các bước thực hiện:
1. **Clone repository:**
   ```bash
   git clone [https://github.com/TonyBucket/InsightBox.git](https://github.com/TonyBucket/InsightBox.git)
   cd InsightBox/SealAI-Router
