from . import news_blueprint
from info.models import News, User, Comment, CommentLike
from flask import render_template, session, g, request, jsonify, current_app
from info import constants, db
from info.utils.commons import get_click_list
from info.utils.wraps import login_wraps
from info.response_code import RET


@news_blueprint.route('/<int:news_id>')
@login_wraps
def detail(news_id):
    news = News.query.get_or_404(news_id)
    # 将点击量加1
    news.clicks += 1
    db.session.commit()
    # 用户登录状态
    # user_id = session.get('user_id')
    # if user_id is None:
    #     user = None
    # else:
    #     user = User.query.get(user_id).to_login_dict()

    # 点击量排行[news,news,....]
    # # 1.根据点击量排序，取前n条新闻
    # news_list1 = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    # # 2.将每个新闻对象转成字典，构造新列表====>列表推导式,[dict,dict,dict,...]
    # news_list2 = [news.to_click_dict() for news in news_list1]
    news_list2 = get_click_list()

    # 当前登录的用户是否收藏了当前新闻
    if g.user and news in g.user.collection_news:
        is_collect = True
    else:
        is_collect = False

    # 查询当前登录的用户是否关注当前新闻的作者
    #news.user====>新闻的作者
    #g.user.authors====>当前登录的用户关注的所有作者，是个列表
    if g.user and news.user in g.user.authors:
        is_follow = True
    else:
        is_follow = False

    # 查询当前新闻的所有评论
    comment_list1 = Comment.query. \
        filter_by(news_id=news_id, comment_id=None). \
        order_by(Comment.create_time.desc())
    comment_list2 = [comment.to_dict() for comment in comment_list1]
    comment_count = comment_list1.count()

    # 查询某个评论是否被当前用户点赞
    if g.user:
        # 查询当前用户对哪些评论点过赞
        like_list1 = CommentLike.query.filter_by(user_id=g.user.id)
        # 当前新闻包含的评论的编号
        news_comment_ids = [comment.id for comment in comment_list1]
        # 查询当前用户点过赞的，当前新闻的数据where comment_id in ()
        like_list1 = like_list1.filter(CommentLike.comment_id.in_(news_comment_ids))
        like_ids = [like.comment_id for like in like_list1]
        # 修改结果字典
        for comment in comment_list2:
            # 判断当前评论是否被点过赞
            comment['like'] = comment.get('id') in like_ids

    data = {
        'news': news,
        'user': g.user.to_login_dict() if g.user else None,
        'news_list': news_list2,
        'is_collect': is_collect,
        'comment_list': comment_list2,
        'comment_count': comment_count,
        'is_follow':is_follow
    }

    return render_template('news/detail.html', data=data)


# @news_blueprint.route('/detail2')
# @login_wraps
# def detail2():
#     pass

@news_blueprint.route('/news_collect', methods=['POST'])
@login_wraps
def news_collect():
    # 1.接收
    news_id = request.json.get('news_id')
    action = request.json.get('action')

    # 2.验证
    # 2.1非空
    if not all([news_id, action]):
        return jsonify(errno=RET.NODATA, errmsg='数据不完整')
    # 2.2新闻编号有效
    try:
        news = News.query.get(news_id)
    except Exception as e:
        # 记录日志
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='连接数据库失败')
    if news is None:
        return jsonify(errno=RET.DATAERR, errmsg='新闻编号无效')
    # 2.3action值有效
    if action not in ('collect', 'cancel_collect'):
        return jsonify(errno=RET.DATAERR, errmsg='操作行为无效')
    # 2.4必须登录
    if g.user is None:
        return jsonify(errno=RET.LOGINERR, errmsg='请先登录')

    # 3.处理:根据action进行收藏或取消
    user = g.user
    if action == 'collect':
        # 收藏
        user.collection_news.append(news)
    else:
        # 取消
        user.collection_news.remove(news)
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='操作失败')

    # 4.响应
    return jsonify(errno=RET.OK, errmsg='')


@news_blueprint.route('/news_comment', methods=['POST'])
@login_wraps
def news_comment():
    '''添加评论数据'''
    # 1.接收
    news_id = request.json.get('news_id')
    content = request.json.get('comment')
    # 评论编号
    comment_id = request.json.get('parent_id')

    # 2.验证
    # 2.1非空
    if not all([news_id, content]):  # ,comment_id
        return jsonify(errno=RET.NODATA, errmsg='数据不完整')
    # 2.2新闻编号有效性
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmg='数据库连接失败')
    if news is None:
        return jsonify(errno=RET.DATAERR, errmsg='新闻编号无效')
    # 2.3验证登录
    if g.user is None:
        return jsonify(errno=RET.LOGINERR, errmsg='请先登录')

    # 3.处理：创建对象并保存
    comment = Comment()
    comment.user_id = g.user.id
    comment.news_id = int(news_id)
    comment.content = content
    # 如果评论编号不为空，表示当前添加回复数据，则指定comment_id属性
    if comment_id:
        comment.comment_id = int(comment_id)
    db.session.add(comment)
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmg='保存失败')

    # 4.响应
    if comment_id:
        data = comment.to_back_dict()
    else:
        data = comment.to_dict()
    return jsonify(errno=RET.OK, errmsg='', data=data)


@news_blueprint.route('/comment_like', methods=['POST'])
@login_wraps
def comment_like():
    # 1.接收
    comment_id = request.json.get('comment_id')
    action = request.json.get('action')

    # 2.验证
    # 2.1非空
    if not all([comment_id, action]):
        return jsonify(errno=RET.NODATA, errmsg='数据不完整')
    # 2.2验证评论编号是否有效
    try:
        comment = Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库连接失败')
    if comment is None:
        return jsonify(errno=RET.DATAERR, errmsg='评论编号无效')
    # 2.3action
    if action not in ('add', 'remove'):
        return jsonify(errno=RET.DATAERR, errmsg='操作方式无效')
    # 2.4登录
    if g.user is None:
        return jsonify(errno=RET.LOGINERR, errmsg='请先登录')

    # 3.处理：向点赞表中添加或删除数据
    if action == 'add':
        # 赞
        like = CommentLike()
        like.user_id = g.user.id
        like.comment_id = int(comment_id)
        db.session.add(like)

        comment.like_count += 1
    else:
        # 取消
        like = CommentLike.query.filter_by(user_id=g.user.id, comment_id=comment_id).first()
        db.session.delete(like)

        comment.like_count -= 1
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='操作失败')

    # 4.响应
    return jsonify(errno=RET.OK, errmsg='')


@news_blueprint.route('/followed_user', methods=['POST'])
@login_wraps
def followed_user():
    # 1.接收
    author_id = request.json.get('user_id')
    action = request.json.get('action')

    # 2.验证
    if not all([author_id, action]):
        return jsonify(errno=RET.NODATA, errmsg='数据不完整')
    if action not in ('follow', 'unfollow'):
        return jsonify(errno=RET.DATAERR, errmsg='操作行为无效')
    try:
        author = User.query.get(author_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库连接失败')
    if author is None:
        return jsonify(errno=RET.DATAERR, errmsg='作者编号无效')
    if g.user is None:
        return jsonify(errno=RET.LOGINERR, errmsg='请先登录')

    # 3.处理
    if action == 'follow':
        # 关注
        if author not in g.user.authors:
            g.user.authors.append(author)
    else:
        # 取消关注
        if author in g.user.authors:
            g.user.authors.remove(author)
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='关注/取消关注失败')

    # 4.响应
    return jsonify(errno=RET.OK, errmsg='')
