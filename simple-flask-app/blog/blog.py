from flask import Blueprint, abort, g, render_template, redirect, request, url_for
from slugify import slugify

from .auth import oidc, okta_client
from .db import Post, db


bp = Blueprint("blog", __name__, url_prefix="/")


def get_posts(author_id):
    """
    Return all of the posts a given user created, ordered by date.
    """
    return Post.query.filter_by(author_id=author_id).order_by(Post.created.desc())


@bp.route("/")
def index():
    """
    Render the homepage.
    """
    posts = Post.query.order_by(Post.created.desc())
    posts_final = []

    for post in posts:
        u = okta_client.get_user(post.author_id)
        post.author_name = u.profile.firstName + " " + u.profile.lastName
        posts_final.append(post)

    return render_template("blog/index.html", posts=posts_final)


@bp.route("/dashboard", methods=["GET", "POST"])
@oidc.require_login
def dashboard():
    """
    Render the dashboard page.
    """
    if request.method == "GET":
        return render_template("blog/dashboard.html", posts=get_posts(g.user.id))

    post = Post(
        title=request.form.get("title"),
        body=request.form.get("body"),
        author_id = g.user.id,
        slug = slugify(request.form.get("title"))
    )

    db.session.add(post)
    db.session.commit()

    return render_template("blog/dashboard.html", posts=get_posts(g.user.id))


@bp.route("/<slug>")
def view_post(slug):
    """View a post."""
    post = Post.query.filter_by(slug=slug).first()
    if not post:
        abort(404)

    u = okta_client.get_user(post.author_id)
    post.author_name = u.profile.firstName + " " + u.profile.lastName

    return render_template("blog/post.html", post=post)


@bp.route("/<slug>/edit", methods=["GET", "POST"])
def edit_post(slug):
    """Edit a post."""
    post = Post.query.filter_by(slug=slug).first()

    if not post:
        abort(404)

    if post.author_id != g.user.id:
        abort(403)

    post.author_name = g.user.profile.firstName + " " + g.user.profile.lastName
    if request.method == "GET":
        return render_template("blog/edit.html", post=post)

    post.title = request.form.get("title")
    post.body = request.form.get("body")
    post.slug = slugify(request.form.get("title"))

    db.session.commit()
    return redirect(url_for(".view_post", slug=post.slug))


@bp.route("/<slug>/delete", methods=["POST"])
def delete_post(slug):
    """Delete a post."""
    post = Post.query.filter_by(slug=slug).first()

    if not post:
        abort(404)

    if post.author_id != g.user.id:
        abort(403)

    db.session.delete(post)
    db.session.commit()

    return redirect(url_for(".dashboard"))