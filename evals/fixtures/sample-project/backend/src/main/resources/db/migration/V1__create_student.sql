CREATE TABLE student (
  id         BIGINT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(100) NOT NULL,
  seller_id  BIGINT       NOT NULL COMMENT '卖家用户ID',
  price      DECIMAL(10,2),
  status     TINYINT      NOT NULL DEFAULT 0,
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted    TINYINT      NOT NULL DEFAULT 0,
  INDEX idx_student_seller (seller_id),
  INDEX idx_student_created_at (created_at)
);
