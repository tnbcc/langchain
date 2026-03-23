-- 创建数据库
CREATE DATABASE IF NOT EXISTS flower_shop CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE flower_shop;

-- 创建鲜花表
CREATE TABLE IF NOT EXISTS flowers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    flower_name VARCHAR(100) NOT NULL COMMENT '鲜花名称',
    flower_type VARCHAR(50) COMMENT '鲜花种类',
    flower_origin VARCHAR(100) COMMENT '鲜花来源',
    purchase_price DECIMAL(10, 2) COMMENT '进货价格',
    sale_price DECIMAL(10, 2) COMMENT '销售价格',
    stock_quantity INT DEFAULT 0 COMMENT '存货数量',
    sold_quantity INT DEFAULT 0 COMMENT '已销售数量',
    shelf_life VARCHAR(50) COMMENT '鲜花保质期',
    description TEXT COMMENT '鲜花描述',
    image_url VARCHAR(500) COMMENT '鲜花图片链接',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '鲜花入库时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='鲜花信息表';

-- 插入5种鲜花假数据
INSERT INTO flowers (flower_name, flower_type, flower_origin, purchase_price, sale_price, stock_quantity, sold_quantity, shelf_life, description, image_url, created_at) VALUES
('红玫瑰', '切花', '云南昆明', 3.50, 8.00, 100, 45, '7天', '红色玫瑰花，象征爱情与浪漫，花朵饱满、色泽鲜艳', 'https://images.example.com/rose-red.jpg', '2026-03-01 10:00:00'),
('康乃馨', '切花', '广东广州', 2.00, 5.50, 80, 30, '10天', '粉色康乃馨，适合送给母亲和长辈，芳香馥郁', 'https://images.example.com/carnation-pink.jpg', '2026-03-05 14:30:00'),
('向日葵', '切花', '黑龙江', 4.00, 10.00, 50, 20, '8天', '黄色向日葵，阳光活力，象征希望与乐观', 'https://images.example.com/sunflower.jpg', '2026-03-10 09:15:00'),
('百合花', '切花', '四川成都', 5.00, 12.00, 60, 35, '7天', '白色百合，纯洁高雅，香气清新宜人', 'https://images.example.com/lily-white.jpg', '2026-03-12 16:45:00'),
('郁金香', '切花', '荷兰进口', 8.00, 18.00, 40, 15, '5天', '紫色郁金香，高贵神秘，花型优雅大方', 'https://images.example.com/tulip-purple.jpg', '2026-03-15 11:20:00');