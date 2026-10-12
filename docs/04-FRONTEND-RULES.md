# 04 – Quy định Frontend

## Stack
React 18, TypeScript `strict`, Vite, Zustand (state toàn cục), TanStack Query (REST), Tailwind CSS, Radix UI primitives (Dialog, Tabs, Switch, Slider, Tooltip) cho a11y, `zod` để parse message WS. Test: Vitest + Testing Library. Không thêm thư viện UI/chart khác khi chưa hỏi.

## Cấu trúc
```
frontend/src/
  api/            rest.ts (fetch client + types), ws.ts (reconnecting WS), schemas.ts (zod)
  stores/         lidarStore, blobStore, calibrationStore, zoneStore, uiStore
  features/
    lidar/        LidarList, LidarCard, FlipAxis, ConnectionForm
    input/        BackgroundPanel, FilterPanel
    blob/         BlobParamsPanel
    output/       OutputPanel
    zones/        ZoneList, ZoneEditor, ZoneTools
    calibration/  CalibrationWizard, CalibrationOverlay
    topview/      TopViewCanvas, layers/*, useViewport.ts
    presets/
  routes/         ControlPage.tsx (/control), WallPage.tsx (/wall)
  components/ui/  nút, tab, slider… theo design tokens
  lib/            geometry.ts, format.ts
```

## Hợp đồng
- Kiểu dữ liệu FE **sinh/khớp** docs/02. Mọi message WS parse bằng zod; message sai → log + bỏ qua, không crash.
- FE **không tự tính** homography/tracking/zone-hit. Chỉ hiển thị và gửi lệnh. (Chỉ được tính hình học để vẽ/chỉnh: chuyển mm↔pixel canvas.)
- State server (config, lidars, zones) lấy qua REST/Query + cập nhật từ WS; không nhân bản thủ công. Thay đổi: gửi API → cập nhật khi thành công (optimistic có rollback cho zone kéo thả).

## Quy ước code
- Component hàm + hooks; file `PascalCase.tsx`; hook `useXxx`; không `any` (dùng `unknown` + zod); không `// @ts-ignore` nếu chưa ghi lý do.
- Đơn vị trong tên: `xMm`, `yMm`, `u`, `v`, `px`. Hàm chuyển toạ độ nằm ở `lib/geometry.ts` có test.
- Không side-effect trong render; effect phải dọn dẹp (WS, rAF, listener).
- Style bằng Tailwind + CSS variables design tokens; không inline style trừ giá trị động (toạ độ).
- Mọi chuỗi UI qua một file `i18n/vi.ts` (mặc định tiếng Việt, sẵn khung `en.ts`).

## Top view (Canvas 2D) – yêu cầu
- Một `<canvas>` HiDPI (`devicePixelRatio`), vẽ bằng `requestAnimationFrame`, **chỉ vẽ lại khi có dữ liệu mới** (dirty flag). Mục tiêu 60 fps với ≥ 4 lidar × 1000 điểm.
- Layer theo thứ tự: nền lưới + vòng 1m/2m/4m (nhãn) → trục X(đỏ)/Y(xanh lá) → điểm thô (đỏ-cam; nền mờ, foreground sáng) → scan area (vàng, 4 handle kéo được) → quad tường đã hiệu chỉnh (magenta, 4 chấm cyan) → blob (cam đậm + vòng) → zone (nếu bật) → HUD (Pos/Size/Angle/Ratio).
- Tương tác: pan (kéo giữa/Space+kéo), zoom (wheel, nút Zoom In/Out/Reset), chọn vùng (`Free`: kéo 4 góc; `Rect`: kéo hình chữ nhật), `Apply` gửi `PUT scan-area`, `Cancel` hoàn tác về giá trị server.
- Điểm thô nhận từ `/ws/points`: decode bằng `DataView`/`Float32Array`, không tạo object cho từng điểm.

## Trang `/wall` (hiển thị trên tường LED)
- Toàn màn hình, nền tối, không thanh cuộn, ẩn con trỏ. Đồng bộ trạng thái bằng WS (`calibration`, `blobs`).
- Vẽ: đích hiệu chỉnh (vòng cyan phát sáng, đích hiện tại màu cam, số thứ tự), đường nét đứt tay↔đích, nhãn `Capturing N samples` / `Distance X px (SPACE to capture)`, tiêu đề `Calibrating Point i/N` + dòng hướng dẫn, vòng cam tại mỗi blob.
- Phím: `Space` → `POST /calibration/capture`, `Esc` → `cancel`, `F` → fullscreen. Phải hoạt động cả khi cửa sổ `/control` ở máy khác.
- Toạ độ vẽ = UV × kích thước viewport (đúng tỉ lệ tường; `wall.widthPx/heightPx` từ config dùng để tính "px" hiển thị).

## Phong cách giao diện (theo video)
Tông tối xanh navy, accent neon: cyan `#22D3EE`, magenta `#E040FB`, vàng `#FACC15`, cam `#FB923C`, đỏ hồng cho nút huỷ `#F43F5E`. Font mono/geometric (Rajdhani / JetBrains Mono) tự host, không phụ thuộc CDN.
Tab trên cùng: `Lidar | Input | Output | Blob | Zones | Settings`. Panel bên phải 360–420 px, top view chiếm phần còn lại. Nút chính màu cyan đặc; nút nguy hiểm viền hồng.
Trạng thái lidar: chấm xanh/vàng/đỏ + FPS. Mọi nút có `title`/tooltip, focus ring rõ, tương phản đạt WCAG AA.

## Hiệu năng & độ bền
- Throttle cập nhật store từ WS (gom theo frame). Selector hẹp để tránh re-render dây chuyền.
- WS tự reconnect (backoff 0.5→5 s), hiển thị banner "Mất kết nối backend"; sau khi nối lại tự lấy lại state.
- Không `console.log` thừa trong bản build.

## Test & DoD (FE)
Vitest cho `lib/geometry.ts`, parser zod, reducer store. Smoke test render `ControlPage` với WS giả. DoD: `npm run typecheck`, `lint`, `test` xanh; không cảnh báo a11y cơ bản; chạy được với Simulator backend; khớp docs/02.
