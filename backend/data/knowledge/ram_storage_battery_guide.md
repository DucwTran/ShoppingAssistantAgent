# Hướng dẫn RAM, ổ cứng, pin và độ di động cho laptop

## RAM

- **8GB**: mức tối thiểu, dễ giật lag khi mở nhiều ứng dụng, không khuyến nghị cho lập trình AI hay đa nhiệm nặng.
- **16GB**: mức khuyến nghị cho lập trình nói chung (chạy IDE, Docker, trình duyệt nhiều tab), đủ cho hầu hết tác vụ AI development ở mức vừa.
- **32GB trở lên**: cần thiết khi làm việc với dataset lớn, chạy nhiều container/service cùng lúc, hoặc load các model AI lớn vào RAM hệ thống (ngoài VRAM).

Với ngân sách hạn chế, ưu tiên tối thiểu 16GB RAM cho nhu cầu lập trình AI và gaming.

## Ổ cứng (Storage)

Nên chọn SSD NVMe thay vì HDD hoặc SSD SATA — tốc độ đọc/ghi nhanh hơn nhiều, giúp load dataset, cài đặt môi trường (Python, Docker image, model weights) nhanh hơn đáng kể. Dung lượng tối thiểu khuyến nghị: 512GB, vì các bộ dataset và model AI có thể chiếm dung lượng lớn.

## Pin (Battery) — quan trọng khi mang đi học/di chuyển nhiều

Laptop gaming/hiệu năng cao (đặc biệt có GPU rời mạnh) thường có thời lượng pin ngắn hơn (3-5 giờ sử dụng thực tế) do tiêu thụ điện năng cao. Laptop mỏng nhẹ hướng văn phòng/sinh viên thường có pin tốt hơn (6-10 giờ) nhưng đánh đổi bằng hiệu năng GPU/CPU thấp hơn.

**Đánh đổi (trade-off) phổ biến**: nếu ưu tiên hiệu năng AI/gaming, cần chấp nhận pin yếu hơn và máy nặng hơn; nếu ưu tiên mang đi học hàng ngày, cần chấp nhận hiệu năng thấp hơn để đổi lấy pin tốt và máy nhẹ.

## Độ di động (Portability)

Laptop gaming hiệu năng cao thường nặng 2-2.5kg trở lên do tản nhiệt lớn. Nếu tiêu chí "mang đi học mỗi ngày" quan trọng, nên cân nhắc các dòng laptop mỏng nhẹ (dưới 2kg) dùng GPU tiết kiệm điện hơn (RTX 4050/4060 phiên bản công suất thấp), chấp nhận hiệu năng thấp hơn một chút để đổi lấy sự tiện lợi khi di chuyển.
