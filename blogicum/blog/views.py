from django.contrib.auth import get_user_model
# from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import (CreateView, DetailView, DeleteView,
                                  ListView, UpdateView)
from .forms import PostForm, CommentForm
from .models import Category, Post, Comment


User = get_user_model()
POSTS_PER_PAGE = 10


class PostCBVMixin:
    """Миксин для определения атрибутов классов для работы с публикациями."""

    model = Post
    form_class = PostForm
    template_name = "blog/create.html"


class AddAuthorMixin:
    """Миксин для добавления значения поля author."""

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class AuthorCheckMixin:
    """Миксин проверки прав доступа к операциям над публикацией."""

    def dispatch(self, request, *args, **kwargs):
        instance = get_object_or_404(Post, pk=self.kwargs['pk'])
        if instance.author != self.request.user:
            return redirect('blog:post_detail',
                            pk=self.kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)


class CommentChangeMixin:
    """Миксин проверки прав доступа к операциям над комментарием
    и перенаправления на страницу публикации после совершения операции.
    """

    model = Comment
    form_class = CommentForm
    template_name = "blog/comment.html"
    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        comment = get_object_or_404(Comment, id=self.kwargs['comment_id'])
        if comment.author != self.request.user:
            return redirect('blog:post_detail',
                            pk=self.kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'pk': self.object.to_post.pk})


class ProfileRedirectMixin:
    """Миксин для переадресации на страницу пользователя."""

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user.username})


class PostCreateView(PostCBVMixin, AddAuthorMixin, ProfileRedirectMixin,
                     LoginRequiredMixin, CreateView):
    """CBV для создания публикаций."""


class PostUpdateView(PostCBVMixin, AddAuthorMixin, AuthorCheckMixin,
                     LoginRequiredMixin, UpdateView):
    """CBV для редактирования публикаций."""

    def get_success_url(self):
        return reverse_lazy('blog:post_detail', kwargs={'pk': self.object.pk})


class PostDeleteView(PostCBVMixin, ProfileRedirectMixin, AuthorCheckMixin,
                     LoginRequiredMixin, DeleteView):
    """CBV для удаления публикаций."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PostForm(instance=self.object)
        return context


# Класс для отображения страницы публикации.
class PostDetailView(DetailView):
    """CBV для отображения страницы публикации."""

    model = Post
    template_name = 'blog/detail.html'

    def dispatch(self, request, *args, **kwargs):
        instance = get_object_or_404(Post, pk=self.kwargs['pk'])
        if instance.author != self.request.user and not instance.is_published:
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = (
            self.object.comments.select_related('author'))
        return context


class PostListView(ListView):
    """CBV для отображения списка публикаций на главной странице."""

    model = Post
    template_name = 'blog/index.html'
    paginate_by = POSTS_PER_PAGE

    def get_queryset(self):
        current_time = timezone.now()
        return Post.objects.select_related(
            'author',
            'location',
            'category'
        ).filter(
            pub_date__lte=current_time,
            is_published=True,
            category__is_published=True)


class CategoryPostsView(ListView):
    """CBV для отображения списка публикаций по отдельной категории."""

    model = Post
    template_name = 'blog/category.html'
    paginate_by = POSTS_PER_PAGE

    @property
    def category(self):
        return self.kwargs.get('category_slug')

    def get_queryset(self):
        current_time = timezone.now()
        return Post.objects.select_related(
            'author',
            'location',
            'category'
        ).filter(
            pub_date__lte=current_time,
            is_published=True,
            category__slug=self.category)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(
            Category, slug=self.category, is_published=True)
        return context


def profile_page(request, username):
    """View-функция отображения страницы пользователя."""
    template = 'blog/profile.html'
    profile = get_object_or_404(User, username=username)
    posts = Post.objects.select_related(
        'category',
        'location',
        'author'
    ).filter(author__username=username)
    if request.user.username != username:
        posts = posts.filter(
            Q(pub_date__lte=timezone.now())
            & Q(is_published=True)
            & Q(category__is_published=True)
        )
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'profile': profile, 'page_obj': page_obj}
    return render(request, template, context)


class ProfileUpdateView(ProfileRedirectMixin, LoginRequiredMixin, UpdateView):
    """CBV для редактирования данных пользователя."""

    model = User
    template_name = 'blog/user.html'
    fields = (
        'username',
        'first_name',
        'last_name',
        'email')

    def get_object(self):
        return self.request.user


class CommentCreateView(LoginRequiredMixin, CreateView):
    """CBV для создания комментариев."""

    to_post = None
    model = Comment
    form_class = CommentForm

    def dispatch(self, request, *args, **kwargs):
        self.to_post = get_object_or_404(Post, pk=kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.to_post = self.to_post
        responce = super().form_valid(form)
        # Увеличиваем счётчик комментариев на 1 в связанной публикации.
        form.instance.to_post.comment_count += 1
        form.instance.to_post.save(update_fields=['comment_count'])
        return responce

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'pk': self.to_post.pk})


class CommentUpdateView(CommentChangeMixin, AddAuthorMixin,
                        LoginRequiredMixin, UpdateView):
    """CBV для редактирования комментариев."""


class CommentDeleteView(CommentChangeMixin, LoginRequiredMixin, DeleteView):
    """CBV для удаления комментариев."""

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        to_post = self.object.to_post
        # Уменьшаем счётчик комментариев на 1 в связанной публикации.
        to_post.comment_count -= 1
        to_post.save(update_fields=['comment_count'])
        return super().delete(request, *args, **kwargs)


# Функцию ниже оставил для себя, просьба не обращать внимания.
# @login_required
# def add_comment(request, post_id):
#     to_post = get_object_or_404(Post, pk=post_id)
#     form = CommentForm(request.POST)
#     if form.is_valid():
#         comment = form.save(commit=False)
#         comment.author = request.user
#         comment.to_post = to_post
#         comment.save()
#         to_post.comment_count += 1
#         to_post.save()
#     return redirect('blog:post_detail', pk=post_id)
