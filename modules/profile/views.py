from . import profile_blueprint
from flask import render_template, g, request, jsonify, current_app
from info.utils.wraps import login_wraps
from info.response_code import RET
from info import db
from info.utils.image_storage import storage
from info.models import News, User, Category


@profile_blueprint.route('/')  # /profile/
@login_wraps
def user():
    data = {
        'user': g.user.to_login_dict()
    }
    return render_template('news/user.html', data=data)


@profile_blueprint.route('/user_base_info', methods=['GET', 'POST'])
@login_wraps
def user_base_info():
    if request.method == 'GET':
        data = {
            'user': g.user.to_dict()
        }
        return render_template('news/user_base_info.html', data=data)
    # 如果是post请求方式，则修改属性
    user = g.user
    # 1.接收
    signature = request.json.get('signature')
    nick_name = request.json.get('nick_name')
    gender = request.json.get('gender')

    # 2.验证
    if not all([signature, nick_name, gender]):
        return jsonify(errno=RET.NODATA, errmsg='信息不完整')
    # 昵称不重复

    # 3.处理：修改属性
    # 修改对象时，不需要使用db.session.add(对象)
    user.signature = signature
    user.nick_name = nick_name
    user.gender = gender
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='修改失败')
    # 4.响应
    return jsonify(errno=RET.OK, errmsg='')


@profile_blueprint.route('/user_pic_info', methods=['GET', 'POST'])
@login_wraps
def user_pic_info():
    if request.method == 'GET':
        data = {
            'user': g.user.to_login_dict()
        }
        return render_template('news/user_pic_info.html', data=data)
    # 修改
    # 1.接收：图片文件
    avatar = request.files.get('avatar')
    # avatar.save('')
    # 2.验证
    if not avatar:
        return jsonify(errno=RET.NODATA, errmsg='请选择头像图片')
    # 3.处理
    # 3.1.将图片保存到七牛
    try:
        avatar_url = storage(avatar.read())
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg='头像图片上传失败')
    # 3.2.修改用户的头像属性
    user = g.user
    user.avatar_url = avatar_url
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='头像修改失败')
    # 4.响应
    return jsonify(errno=RET.OK, errmsg='', data=user.to_login_dict())


@profile_blueprint.route('/user_pass_info', methods=['GET', 'POST'])
@login_wraps
def user_pass_info():
    if request.method == 'GET':
        return render_template('news/user_pass_info.html')
    # 修改
    # 1.接收
    old_password = request.json.get('old_password')
    new_password = request.json.get('new_password')
    new_password2 = request.json.get('new_password2')

    # 2.验证
    if not all([old_password, new_password, new_password2]):
        return jsonify(errno=RET.NODATA, errmsg='数据不完整')
    if new_password != new_password2:
        return jsonify(errno=RET.DATAERR, errmsg='两次密码不一致')
    if not g.user.check_password(old_password):
        return jsonify(errno=RET.DATAERR, errmsg='原密码错误')

    # 3.处理
    g.user.password = new_password
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='密码修改失败')
    # 4.响应
    return jsonify(errno=RET.OK, errmsg='')


@profile_blueprint.route('/user_collection')
@login_wraps
def user_collection():
    '''查询当前用户收藏的新闻，并分页显示'''
    # 接收页码
    try:
        page = int(request.args.get('page', 1))
    except:
        page = 1
    # 查询
    try:
        pagination = g.user.collection_news. \
            order_by(News.id.desc()). \
            paginate(page, 6, False)
        data = {
            'news_list': [news.to_index_dict() for news in pagination.items],
            'page': page,
            'total_page': pagination.pages
        }
    except Exception as e:
        current_app.logger.error(e)
        data = {
            'news_list': [],
            'page': 1,
            'total_page': 0
        }
    return render_template('news/user_collection.html', data=data)


@profile_blueprint.route('/user_follow')
@login_wraps
def user_follow():
    '''查询当前登录用户关注的作者，可分页'''
    try:
        page = int(request.args.get('page', 1))
    except:
        page = 1

    try:
        pagination = g.user.authors. \
            order_by(User.id.desc()). \
            paginate(page, 4, False)
        data = {
            'author_list': [author.to_dict() for author in pagination.items],
            'page': page,
            'total_page': pagination.pages
        }
    except Exception as e:
        current_app.logger.error(e)
        data = {
            'author_list': [],
            'page': 1,
            'total_page': 0
        }
    return render_template('news/user_follow.html', data=data)


@profile_blueprint.route('/user_news_release', methods=['GET', 'POST'])
@login_wraps
def user_news_release():
    '''发布新闻'''
    if request.method == 'GET':
        # 查询所有分类
        category_list = Category.query.all()
        data = {
            'category_list': [category.to_dict() for category in category_list]
        }
        return render_template('news/user_news_release.html', data=data)
    # post请求===》添加新闻数据
    # 1.接收
    title = request.form.get('title')
    category_id = request.form.get('category_id')
    digest = request.form.get('digest')
    content = request.form.get('content')

    # 接收文件
    index_image = request.files.get('index_image')
    # 文件大小
    # 文件像素

    # 2.验证
    if not all([title, category_id, digest, content, index_image]):
        return jsonify(errno=RET.NODATA, errmsg='数据不完整')
    try:
        category = Category.query.get(category_id)  # select * from ...where id=...
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库连接失败')
    if category is None:
        return jsonify(errno=RET.DATAERR, errmsg='分类编号无效')
    # 判断字符串的长度

    # 3.处理
    # 3.1保存图片
    try:
        index_image_url = storage(index_image.read())
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg='保存图片失败')

    # 3.2新建对象
    news = News()
    news.title = title
    news.source = g.user.nick_name
    news.digest = digest
    news.content = content
    news.index_image_url = index_image_url
    news.category_id = category.id
    news.user_id = g.user.id
    db.session.add(news)
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='新闻发布失败')

    # 4.响应
    return jsonify(errno=RET.OK, errmsg='')


@profile_blueprint.route('/user_news_list')
@login_wraps
def user_news_list():
    '''查询当前用户发布的新闻，带分页'''
    try:
        page = int(request.args.get('page', 1))
    except:
        page = 1

    try:
        pagination = g.user.news_list.order_by(News.id.desc()).paginate(page, 6, False)
        data = {
            'news_list': [news.to_release_dict() for news in pagination.items],
            'page': page,
            'total_page': pagination.pages
        }
    except Exception as e:
        current_app.logger.error(e)
        data = {
            'news_list': [],
            'page': 1,
            'total_page': 0
        }

    return render_template('news/user_news_list.html', data=data)
