-- 单行/压缩 DDL 回归样例（v3.1.1）：整条建表语句写在一行，
-- 且含 DECIMAL(10,2) 这类括号内逗号，用于证明列解析不依赖物理换行。
CREATE TABLE `order_item` (`id` bigint NOT NULL AUTO_INCREMENT, `order_id` bigint NOT NULL, `amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00, `created_at` datetime DEFAULT CURRENT_TIMESTAMP, `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, `deleted` tinyint NOT NULL DEFAULT 0, PRIMARY KEY (`id`), INDEX idx_order_item_order (`order_id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
