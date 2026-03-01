# 📦 InsightBox & SealAI™ Router 
**Multimodal Knowledge Capture and Retrieval Framework for Education**

![Status: PoC](https://img.shields.io/badge/Status-Proof_of_Concept-orange)
![License: MIT](https://img.shields.io/badge/License-MIT-blue)

## 🌟 Tầm nhìn dự án (Vision)
InsightBox biến không gian lớp học vật lý từ một sự kiện trôi qua một lần trở thành một **Searchable Knowledge Timeline**. Hệ thống số hóa lời giảng và nét phấn trên bảng, xây dựng một lớp "Sự thật gốc" (Ground Truth Layer) để học sinh truy xuất lại kiến thức bị đứt gãy.

## ⚙️ Kiến trúc Hệ thống (System Architecture)
Hệ thống được thiết kế theo chuẩn Hybrid Edge-Cloud Microservices:
1. **Edge Node (InsightBox):** Thu thập dữ liệu thông minh với YOLOv8n (chạy trên NPU) để nhận diện vùng che bảng, tiết kiệm 99% băng thông.
2. **Local Lab GPU:** Chạy pipeline lọc ồn, bóc băng (Qwen3-ASR) và chuẩn hóa toán học (Gemma 3).
3. **SealAI™ Router (Core):** Trình định tuyến Self-Routing LLM đánh giá độ phức tạp truy vấn để cân bằng tải giữa Local và Cloud AI.

## 🚀 Trạng thái Phát triển (Development Status)
Dự án hiện đang trong giai đoạn **Proof of Concept (PoC)**.

- ✔ SealAI Router – Completed

- ✔ Local LLM + Qwen3 ASR – Operational

- ⚙ Vector Database (Qdrant) – Integration phase

- ⚙ Student App Frontend – UI/UX design phase

- ⚙ Edge Hardware Node – Prototype testing


## 📂 Cấu trúc Repository
- `/sealai-router/`: Mã nguồn lõi định tuyến AI.
- `/insightbox-edge-node/`: [WIP] Phần cứng & Cảm biến.
- `/local-lab-processing/`: [WIP] Pipeline xử lý dữ liệu.
- `/student-app-ui/`: [WIP] Giao diện ứng dụng.

*(Dự án thuộc khuôn khổ cuộc thi AI Young Guru)*
