from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone

from .forms import CommentForm, PostForm
from .models import Comment, Post


POSTS_PER_PAGE = 10


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
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        comment = get_object_or_404(Comment, id=self.kwargs['comment_id'])
        if comment.author != self.request.user:
            return redirect('blog:post_detail',
                            pk=self.kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('blog:post_detail',
                       kwargs={'pk': self.object.to_post.pk})


class GetPostsMixin:
    """Миксин для отбора публикаций."""

    @staticmethod
    def get_all_posts():
        """Функция отбора QuerySet со всеми постами"""
        return Post.objects.select_related(
            'category',
            'location',
            'author'
        )

    def get_published_posts(self):
        """Функция отбора QuerySet с опубликованными постами"""
        current_time = timezone.now()
        return self.get_all_posts().filter(
            pub_date__lte=current_time,
            is_published=True)


class PostCBVMixin:
    """Миксин для определения атрибутов CBV для работы с публикациями."""

    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'


class PostListMixin:
    """Миксин для определения атрибутов CBV для вывода списка публикаций."""

    model = Post
    paginate_by = POSTS_PER_PAGE


class ProfileRedirectMixin:
    """Миксин для переадресации на страницу пользователя."""

    def get_success_url(self):
        return reverse('blog:profile',
                       kwargs={'username': self.request.user.username})
