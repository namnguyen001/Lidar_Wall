# Lidar Interactive Wall – Vibecode Kit

Bộ tài liệu để vibecode (Claude Code / Cursor / Claude.ai Projects) một ứng dụng **tường tương tác dùng LiDAR 2D**,
lấy cảm hứng từ video "Fast Lidar Calibration System" (LiDAR x TouchDesigner).

## Phần cứng của bạn
| Thiết bị | Kết nối | Ghi chú |
|---|---|---|
| YDLIDAR **TEA** (ToF) | Ethernet/TCP `192.168.0.11` (port: 8090) | PC phải cùng dải mạng 192.168.0.x |
| YDLIDAR **G4** (triangulation) | Serial `COM3`, baudrate `230400` | Windows |

## Cách dùng kit (3 bước)
1. Giải nén, đặt nguyên thư mục làm **root repo**. Mở bằng Claude Code (`claude` trong thư mục này).
   `CLAUDE.md` và skill `.claude/skills/lidar-interactive-wall/` sẽ được nạp tự động.
2. Chạy lần lượt các file trong `prompts/` theo số thứ tự (00 → 10). **Mỗi prompt = 1 phiên làm việc**, chạy xong phải qua phần "Nghiệm thu" mới sang prompt kế.
3. Mỗi lần AI làm sai quy ước, nhắc: *"Đọc lại CLAUDE.md và docs/03 (hoặc 04) rồi sửa"*.

## Mục lục
```
CLAUDE.md                      Quy tắc tổng, luôn được nạp
.claude/skills/lidar-interactive-wall/   Skill: kiến thức miền (pipeline, hiệu chỉnh, driver, zone, multi-lidar)
docs/00-PRD.md                 Yêu cầu sản phẩm, chức năng theo video
docs/01-ARCHITECTURE.md        Kiến trúc, luồng dữ liệu, threading
docs/02-API-CONTRACT.md        REST + WebSocket (FE và BE phải tuân thủ)
docs/03-BACKEND-RULES.md       Quy định Backend
docs/04-FRONTEND-RULES.md      Quy định Frontend + UI theo phong cách video
docs/05-DATA-MODELS.md         Mô hình dữ liệu, hệ toạ độ, driver YDLIDAR
docs/06-TESTING-QA.md          Kiểm thử, simulator, checklist phần cứng
docs/07-ROADMAP.md             Lộ trình, definition of done
prompts/00..10-*.md            Chuỗi prompt vibecode
config/default.config.json     Cấu hình mẫu (đã điền TEA + G4)
config/config.schema.json      JSON Schema cho config
backend/requirements.txt       Thư viện Python gợi ý
```

## Lưu ý quan trọng
- Phân tích video dựa trên khung hình bị mờ; tên tab cuối cùng (`S…`) là suy đoán.
