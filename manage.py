from flask_script import Manager
from info import create_app, db
from info import models

# 可用的键包含：'develop','product'
# 工厂设计模式：在发生变化时，可以让代码的修改量降到最低
app = create_app('develop')
# app=create_app('product')
manager = Manager(app)

from flask_migrate import Migrate, MigrateCommand

Migrate(app, db)
manager.add_command('db', MigrateCommand)


# 自定义终端命令==>python manage.py createsuperuser -p 456 -u 123
@manager.option('-u',dest='name')
@manager.option('-p',dest='password')
def createsuperuser(name, password):
    try:
        if models.User.query.filter_by(mobile=name).count() > 0:
            print('用户名已经存在')
            return
    except:
        print('数据库连接失败')
        return

    user = models.User()
    user.nick_name = name
    user.mobile = name
    user.password = password
    user.is_admin = True  # 管理员
    db.session.add(user)
    try:
        db.session.commit()
        print('管理员创建成功')
    except:
        print('连接数据库失败')


if __name__ == '__main__':
    # print(app.url_map)
    manager.run()
