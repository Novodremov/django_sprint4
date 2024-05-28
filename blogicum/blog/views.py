from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import (CreateView, DeleteView, DetailView,
                                  ListView, UpdateView)

from .forms import CommentForm, PostForm
from .mixins import (AddAuthorMixin, AuthorCheckMixin, CommentChangeMixin,
                     GetPostsMixin, PostCBVMixin, PostListMixin,
                     ProfileRedirectMixin)
from .models import Category, Comment, Post


User = get_user_model()


class PostCreateView(PostCBVMixin, AddAuthorMixin, ProfileRedirectMixin,
                     LoginRequiredMixin, CreateView):
    """CBV для создания публикаций."""


class PostUpdateView(PostCBVMixin, AddAuthorMixin, AuthorCheckMixin,
                     LoginRequiredMixin, UpdateView):
    """CBV для редактирования публикаций."""

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'pk': self.object.pk})


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


class PostListView(GetPostsMixin, PostListMixin, ListView):
    """CBV для отображения списка публикаций на главной странице."""

    template_name = 'blog/index.html'

    def get_queryset(self):
        return self.get_published_posts().filter(
            category__is_published=True)


class CategoryPostsView(GetPostsMixin, PostListMixin, ListView):
    """CBV для отображения списка публикаций по отдельной категории."""

    template_name = 'blog/category.html'

    @property
    def category(self):
        return self.kwargs.get('category_slug')

    def get_queryset(self):
        return self.get_published_posts().filter(
            category__slug=self.category)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(
            Category, slug=self.category, is_published=True)
        return context


class ProfilePageView(GetPostsMixin, PostListMixin, ListView):
    """CBV для отображения страницы пользователя."""

    template_name = 'blog/profile.html'

    @property
    def username(self):
        return self.kwargs.get('username')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = get_object_or_404(
            User, username=self.username)
        return context

    def get_queryset(self):
        if self.request.user.username == self.username:
            posts = self.get_all_posts()
        else:
            posts = self.get_published_posts().filter(
                category__is_published=True)
        return posts.filter(author__username=self.username)


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
