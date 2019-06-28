from flask import Flask,render_template,g
from info.config import config_dict
# from info.config import DevelopConfig
from flask_sqlalchemy import SQLAlchemy
from redis import StrictRedis
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
import os
import logging
from logging.handlers import RotatingFileHandler

# 创建数据库连接对象
db = SQLAlchemy()
redis_store = None

from info.utils.wraps import login_wraps


def setup_log(config_name):
    """配置日志"""
    dir_file = os.path.abspath(__file__)
    dir_info = os.path.dirname(dir_file)
    dir_base = os.path.dirname(dir_info)
    dir_log = os.path.join(dir_base, 'logs/log')

    # 设置日志的记录等级
    logging.basicConfig(level=config_dict[config_name].LOG_LEVEL)  # 调试debug级
    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
    file_log_handler = RotatingFileHandler(dir_log, maxBytes=1024 * 1024 * 100, backupCount=10)
    # 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)


def create_app(config_str):
    app = Flask(__name__)

    app.config.from_object(config_dict.get(config_str))

    # 初始化mysql
    # db = SQLAlchemy(app)
    db.init_app(app)
    global redis_store
    redis_store = StrictRedis(
        host=app.config.get('REDIS_HOST'),
        port=app.config.get('REDIS_PORT'),
        db=app.config.get('REDIS_DB')
    )

    # 设置CSRF保护
    CSRFProtect(app)

    # 设置Session：默认flask将session保存到cookie中，通过flask_session中的Session类可以扩展存储方案
    Session(app)

    # 启用日志
    setup_log(config_str)


    #注册请求勾子函数，输出csrf口令
    @app.after_request
    def after(response):
        #生成口令字符串
        from flask_wtf.csrf import generate_csrf
        token=generate_csrf()
        #输出到cookie中
        response.set_cookie('csrf_token',token)
        return response

    @app.errorhandler(404)
    @login_wraps
    def handle404(e):
        data={
            'user':g.user.to_dict()
        }
        return render_template('news/404.html',data=data)


    # 注册蓝图
    from info.modules.index import index_blueprint
    app.register_blueprint(index_blueprint)

    from info.modules.passport import passport_blueprint
    app.register_blueprint(passport_blueprint)

    from info.modules.news import news_blueprint
    app.register_blueprint(news_blueprint)

    from info.modules.profile import profile_blueprint
    app.register_blueprint(profile_blueprint)

    from info.modules.admin import admin_blueprint
    app.register_blueprint(admin_blueprint)

    return app
