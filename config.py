import redis
import logging


class Config(object):
    """工程配置信息"""
    SECRET_KEY = "EjpNVSNQTyGi1VvWECj9TvC/+kq3oujee2kTfQUs8yCM6xX9Yjq52v54g+HVoknA"

    DEBUG = False

    # 数据库的配置信息
    SQLALCHEMY_DATABASE_URI = "mysql://root:123456@127.0.0.1:3306/xw"
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    # redis配置
    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379
    REDIS_DB = 12

    # session 配置
    SESSION_TYPE = "redis"  # 指定 session 保存到 redis 中
    SESSION_USE_SIGNER = True  # 让 cookie 中的 session_id 被加密签名处理
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)  # 使用 redis 的实例
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # session 的有效期，单位是秒

    # 默认日志等级
    LOG_LEVEL = logging.DEBUG


# 在开发时使用一套配置
class DevelopConfig(Config):
    DEBUG = True


# 在上线时使用一套配置
class ProductConfig(Config):
    LOG_LEVEL = logging.ERROR


config_dict = {
    'develop': DevelopConfig,
    'product': ProductConfig
}
