-- PostgreSQL 初始化脚本
-- 用法: psql -U postgres -f init_pg.sql
-- 应用层使用 SQLAlchemy create_all() 创建表结构，
-- 此脚本仅用于创建数据库和用户。

CREATE DATABASE market_memory
  ENCODING 'UTF8'
  LC_COLLATE 'en_US.UTF-8'
  LC_CTYPE 'en_US.UTF-8'
  TEMPLATE template0;

-- 可选：创建专用用户（取消注释并修改密码）
-- CREATE USER market_engine WITH PASSWORD 'change_me';
-- GRANT ALL PRIVILEGES ON DATABASE market_memory TO market_engine;
-- ALTER DATABASE market_memory OWNER TO market_engine;
