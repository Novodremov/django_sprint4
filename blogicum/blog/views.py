from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Category, Post


NUM_OF_POSTS_ON_MAIN = 5


def get_posts():
    current_time = timezone.now()
    return Post.objects.select_related('category', 'location').filter(
        Q(pub_date__lte=current_time)
        & Q(is_published=True)
        & Q(category__is_published=True))


def index(request):
    template = 'blog/index.html'
    posts = get_posts()[:NUM_OF_POSTS_ON_MAIN]
    context = {
        'post_list': posts
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'blog/detail.html'
    post = get_object_or_404(get_posts(), pk=post_id)
    context = {
        'post': post
    }
    return render(request, template, context)


def category_posts(request, category_slug):
    template = 'blog/category.html'
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True)
    posts = get_posts().filter(category__slug=category_slug)
    context = {
        'post_list': posts,
        'category': category
    }
    return render(request, template, context)
