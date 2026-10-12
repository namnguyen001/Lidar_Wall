# Prompt 09 – Output OSC / TUIO / WebSocket và mẫu TouchDesigner

Đọc `docs/02` (Output ra ngoài), `docs/01`, skill SKILL.md (Output conventions).

## Việc cần làm
1. `output/osc.py` (python-osc): `/wall/count`, `/wall/blob`, `/wall/blob/up`, `/wall/zone/<id>/{enter,hold,exit,count}` đúng payload docs/02; tốc độ gửi theo `rateHz`; không chặn vòng xử lý (queue nhỏ, bỏ cũ khi đầy).
2. `output/tuio.py`: TUIO 1.1 `/tuio/2Dcur` (`source`, `alive`, `set`, `fseq`) qua UDP.
3. `output/ws_out.py`: server WS riêng (port `ws.port`) phát `blobs`/`zoneEvent`.
4. `coordinate`: `space: uv|px`, `flipY`, kích thước tường px khi xuất px.
5. `POST /api/output/test`: gửi blob giả quỹ đạo tròn trong 3 s.
6. Thư mục `examples/touchdesigner/`: hướng dẫn `README.md` nối `OSC In DAT`/`TUIO In` → `Script CHOP`/`DAT to CHOP` → vẽ vòng tại (u,v); file mẫu `.toe` **chỉ khi** tạo được an toàn, nếu không thì mô tả từng bước và đoạn Python cho Script CHOP.
7. Ví dụ client Python nhận OSC (`examples/osc_listener.py`) để tự kiểm.

## Nghiệm thu
- Test tự động: server OSC giả nhận đúng message/kiểu dữ liệu.
- TouchDesigner (hoặc OSC monitor) thấy blob theo tay, `blob/up` khi bỏ tay, sự kiện zone đúng.
- Bật/tắt từng output nóng không cần restart.
