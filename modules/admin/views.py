from info import constants, db
from info.response_code import RET
from info.utils.image_storage import storage
from . import admin_blueprint
from flask import render_template, request, current_app, redirect, session, g, jsonify
from info.models import User, News, Category
from datetime import datetime, timedelta


@admin_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        data = {'msg': ''}
        return render_template('admin/login.html', data=data)
    # post请求，查询数据做判断
    # 1.接收
    username = request.form.get('username')
    password = request.form.get('password')
    # 2.验证
    if not all([username, password]):
        data = {'msg': '数据填写不完整'}
        return render_template('admin/login.html', data=data)
    # 3.处理
    # 根据用户名查询用户
    try:
        user = User.query.filter_by(mobile=username, is_admin=True).first()
    except Exception as e:
        current_app.logger.error(e)
        data = {'msg': '数据库连接失败'}
        return render_template('admin/login.html', data=data)
    # 判断用户名是否正确
    if user is None:
        data = {'msg': '用户名错误'}
        return render_template('admin/login.html', data=data)
    # 判断密码是否正确
    if user.check_password(password):
        # 状态保持：session
        session['admin_user_id'] = user.id
        return redirect('/admin/')
    else:
        data = {'msg': '密码错误'}
        return render_template('admin/login.html', data=data)
        # 4.响应


@admin_blueprint.route('/logout')
def logout():
    session.pop('admin_user_id')
    return redirect('/admin/login')


@admin_blueprint.route('/')
def index():
    # 先登录，再访问
    # if 'admin_user_id' not in session:
    #     return redirect('/admin/login')
    data = {
        'user': g.user.to_login_dict()
    }
    return render_template('admin/index.html', data=data)


@admin_blueprint.route('/user_count')
def user_count():
    now = datetime.now()
    # 用户总数
    count_total = User.query.filter_by(is_admin=False).count()
    # 用户月新增数
    month0 = datetime(now.year, now.month, 1)  # 获取当前月的1日0时0分0秒
    count_month = User.query.filter_by(is_admin=False). \
        filter(User.create_time >= month0).count()
    # 用户日新增数
    day0 = datetime(now.year, now.month, now.day)
    count_day = User.query.filter_by(is_admin=False). \
        filter(User.create_time >= day0).count()
    # 用户登录活跃数：近30天
    xlist = []
    ylist = []
    for i in range(10):
        # 计算开始的第n天
        date_begin = day0 - timedelta(days=i + 1)
        # 计算结束的第n天
        date_end = day0 - timedelta(days=i)
        # if i==0:
        #     print(date_begin)
        #     print(date_end)
        xlist.append(date_begin.strftime('%Y-%m-%d'))
        # 统计第n天登录个数
        count = User.query.filter_by(is_admin=False). \
            filter(User.update_time >= date_begin, User.update_time < date_end).count()
        # print('%d--%d'%(i,count))
        ylist.append(count)
    # 列表反转
    xlist.reverse()
    ylist.reverse()

    data = {
        'count_total': count_total,
        'count_month': count_month,
        'count_day': count_day,
        'xlist': xlist,
        'ylist': ylist
    }
    return render_template('admin/user_count.html', data=data)


@admin_blueprint.route('/user_list')
def user_list():
    try:
        page = int(request.args.get('page', 1))
    except:
        page = 1

    try:
        pagination = User.query.filter_by(is_admin=False). \
            order_by(User.id.desc()). \
            paginate(page, constants.ADMIN_USER_PAGE_MAX_COUNT, False)
        data = {
            'user_list': [user.to_admin_dict() for user in pagination.items],
            'page': page,
            'total_page': pagination.pages
        }
    except Exception as e:
        current_app.logger.error(e)
        data = {
            'user_list': [],
            'page': 1,
            'total_page': 0
        }

    return render_template('admin/user_list.html', data=data)


@admin_blueprint.route('/news_review')
def news_review():
    title = request.args.get('title', '')

    try:
        page = int(request.args.get('page', 1))
    except:
        page = 1
    try:
        pagination = News.query.filter_by(status=1)

        if title:
            pagination = pagination.filter(News.title.contains(title))  # like '%...%'

        pagination = pagination.order_by(News.id.desc()). \
            paginate(page, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)
        data = {
            'news_list': [news.to_release_dict() for news in pagination.items],
            'page': page,
            'total_page': pagination.pages,
            'title': title
        }
    except Exception as e:
        current_app.logger.error(e)
        data = {}
    return render_template('admin/news_review.html', data=data)


@admin_blueprint.route('/news_review_detail', methods=['GET', 'POST'])
def news_review_detail():
    if request.method == 'GET':
        news_id = request.args.get('news_id')

        try:
            news = News.query.get(news_id)
            data = {'news': news.to_index_dict()}
        except Exception as e:
            current_app.logger.error(e)
            data = {}

        return render_template('admin/news_review_detail.html', data=data)
    # post===>审核，修改属性
    # 1.接收
    action = request.json.get('action')
    news_id = request.json.get('news_id')
    reason = request.json.get('reason')

    # 2.验证
    if not all([action, news_id]):
        return jsonify(errno=RET.NODATA, errmsg='数据不完整')
    if action not in ['accept', 'reject']:
        return jsonify(errno=RET.DATAERR, errmsg='操作方式无效')
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库连接失败')
    if news is None:
        return jsonify(errno=RET.DATAERR, errmsg='新闻编号无效')
    if action == 'reject' and not reason:
        return jsonify(errno=RET.NODATA, errmsg='请填写拒绝原因')

    # 3.处理
    if action == 'accept':
        news.status = 0
    else:
        news.status = -1
        news.reason = reason

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='审核失败')

    # 4.响应
    return jsonify(errno=RET.OK, errmsg='')


@admin_blueprint.route('/news_edit')
def news_edit():
    title = request.args.get('title', '')

    try:
        page = int(request.args.get('page', 1))
    except:
        page = 1

    pagination = News.query.filter_by(status=0)

    if title:
        pagination = pagination.filter(News.title.contains(title))

    try:
        pagination = pagination.order_by(News.id.desc()). \
            paginate(page, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)

        data = {
            'news_list': [news.to_release_dict() for news in pagination.items],
            'page': page,
            'total_page': pagination.pages,
            'title': title
        }
    except Exception as e:
        current_app.logger.error(e)
        data = {}

    return render_template('admin/news_edit.html', data=data)


@admin_blueprint.route('/news_edit_detail', methods=['GET', 'POST'])
def news_edit_detail():
    if request.method == 'GET':
        news_id = request.args.get('news_id')

        try:
            news = News.query.get(news_id)
            category_list = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return redirect('/admin/news_edit')

        if news is None:
            return redirect('/admin/news_edit')

        data = {
            'news': news.to_index_dict(),
            'category_list': [category.to_dict() for category in category_list]
        }

        return render_template('admin/news_edit_detail.html', data=data)

    # post===>修改
    # 1.接收
    news_id = request.form.get('news_id')
    title = request.form.get('title')
    category_id = request.form.get('category_id')
    digest = request.form.get('digest')
    content = request.form.get('content')

    index_image = request.files.get('index_image')

    # 2.验证
    if not all([news_id, title, category_id, digest, content]):
        return jsonify(errno=RET.NODATA, errmsg='数据不完整')
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库连接失败')
    if news is None:
        return jsonify(errno=RET.DATAERR, errmsg='新闻编号无效')

    # 3.处理
    # 3.1上传文件
    if index_image:
        try:
            index_image_url = storage(index_image.read())
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.THIRDERR, errmsg='图片上传到七牛失败')

    # 3.2修改属性
    news.title = title
    news.digest = digest
    news.content = content
    if index_image:
        news.index_image_url = index_image_url
    news.category_id = int(category_id)
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='新闻修改失败')

    # 4.响应
    return jsonify(errno=RET.OK, errmsg='')


@admin_blueprint.route('/news_type')
def news_type():
    try:
        category_list = Category.query.all()
        data = {
            'category_list': [category.to_dict() for category in category_list]
        }
    except Exception as e:
        current_app.logger.error(e)
        data = {}

    return render_template('admin/news_type.html', data=data)


@admin_blueprint.route('/add_category', methods=['POST'])
def add_category():
    # 分类编号，如果为空表示添加，如果非空表示修改
    cid = request.json.get('id')
    name = request.json.get('name')

    if not all([name]):
        return jsonify(errno=RET.NODATA, errmsg='请填写分类名称')
    if Category.query.filter_by(name=name).count() > 0:
        return jsonify(errno=RET.DATAEXIST, errmsg='此名称已经存在')

    if cid:
        # 修改
        try:
            category = Category.query.get(cid)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg='数据库连接失败')
        if category is None:
            return jsonify(errno=RET.DATAERR, errmsg='分类编号无效')
        category.name = name
    else:
        # 添加
        category = Category()
        category.name = name
        db.session.add(category)

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='保存失败')
    return jsonify(errno=RET.OK, errmsg='')
