-- 订单系统 SQL
-- flower_shop 订单表

-- 创建订单表
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(32) PRIMARY KEY COMMENT '订单号',
    flower_id INT NOT NULL COMMENT '商品ID',
    quantity INT NOT NULL DEFAULT 1 COMMENT '购买数量',
    unit_price DECIMAL(10, 2) NOT NULL COMMENT '单价',
    total_price DECIMAL(10, 2) NOT NULL COMMENT '总价',
    phone VARCHAR(20) COMMENT '联系电话',
    shipping_status VARCHAR(20) DEFAULT 'pending' COMMENT '发货状态: pending-待发货, shipped-已发货, delivered-已送达',
    shipping_time TIMESTAMP NULL COMMENT '发货时间',
    return_status VARCHAR(20) DEFAULT 'none' COMMENT '退货状态: none-无退货, applied-申请退货, approved-已批准, rejected-已拒绝, completed-已完成退货',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '订单生成时间',
    return_time TIMESTAMP NULL COMMENT '退货时间',
    FOREIGN KEY (flower_id) REFERENCES flowers(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单信息表';

-- 清空旧数据
TRUNCATE TABLE orders;

-- 插入订单假数据
INSERT INTO orders (order_id, flower_id, quantity, unit_price, total_price, phone, shipping_status, shipping_time, return_status, created_at) VALUES
('ORD20260324001', 1, 2, 8.00, 16.00, '13800138001', 'shipped', '2026-03-21 10:00:00', 'none', '2026-03-20 10:30:00'),
('ORD20260324002', 2, 1, 5.50, 5.50, '13800138002', 'delivered', '2026-03-19 15:00:00', 'none', '2026-03-18 14:20:00'),
('ORD20260324003', 3, 3, 10.00, 30.00, '13800138003', 'shipped', '2026-03-22 09:30:00', 'none', '2026-03-21 09:15:00'),
('ORD20260324004', 4, 1, 12.00, 12.00, '13800138004', 'pending', NULL, 'none', '2026-03-22 16:45:00'),
('ORD20260324005', 5, 2, 18.00, 36.00, '13800138005', 'delivered', '2026-03-16 14:00:00', 'applied', '2026-03-15 11:00:00'),
('ORD20260324006', 1, 5, 8.00, 40.00, '13800138006', 'delivered', '2026-03-11 10:00:00', 'completed', '2026-03-10 13:30:00', '2026-03-12 10:00:00'),
('ORD20260324007', 2, 2, 5.50, 11.00, '13800138007', 'shipped', '2026-03-23 16:00:00', 'none', '2026-03-23 08:45:00'),
('ORD20260324008', 3, 1, 10.00, 10.00, '13800138008', 'pending', NULL, 'none', '2026-03-23 15:20:00'),
('ORD20260324009', 4, 4, 12.00, 48.00, '13800138009', 'delivered', '2026-03-20 11:00:00', 'none', '2026-03-19 10:10:00'),
('ORD20260324010', 5, 1, 18.00, 18.00, '13800138010', 'shipped', '2026-03-23 09:00:00', 'none', '2026-03-22 14:55:00');

-- 查询订单（带商品信息）
SELECT 
    o.order_id,
    f.flower_name,
    f.flower_type,
    o.quantity,
    o.unit_price,
    o.total_price,
    o.phone,
    o.shipping_status,
    o.shipping_time,
    o.return_status,
    o.created_at,
    o.return_time
FROM orders o
JOIN flowers f ON o.flower_id = f.id
ORDER BY o.created_at DESC;
