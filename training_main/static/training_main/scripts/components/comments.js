/* global ajax:false */

window.comments = (function comments() {
  class Comment {
    constructor(element) {
      this.id = element.dataset.commentId;
      this.likeUrl = element.dataset.likeUrl;
      this.element = element;
      this._setupEventListeners();
    }

    get replyLink() {
      return this.element.querySelector('.comment-reply');
    }

    get likeButton() {
      return this.element.querySelector('.checkbox-like');
    }

    get commentLikesCountElement() {
      return this.element.querySelector('.comment-likes-count');
    }

    get commentSection() {
      const commentSectionElement = this.element.closest(`.${CommentSection.className}`);
      if (commentSectionElement == null) {
        return null;
      } else {
        return CommentSection.getOrWrap(commentSectionElement);
      }
    }

    get inputsElement() {
      const inputsElement = [...this.element.children].filter(e =>
        e.classList.contains('comment-inputs')
      )[0];

      if (inputsElement == null) {
        return null;
      } else {
        return inputsElement;
      }
    }

    get replyCommentInput() {
      const { inputsElement } = this;
      if (inputsElement == null) {
        return null;
      }

      const replyCommentInputElement = inputsElement.querySelector('.comment-input');
      if (replyCommentInputElement == null) {
        return null;
      }

      return CommentInput.getOrWrap(replyCommentInputElement);
    }

    _setupEventListeners() {
      this.replyLink.addEventListener('click', event => {
        event.preventDefault();
        this._showReplyCommentInput();
      });

      this.likeButton.addEventListener('click', this._postLike.bind(this));
    }

    _getOrCreateReplyCommentInput() {
      const { commentSection, replyCommentInput, inputsElement } = this;
      if (replyCommentInput == null) {
        const commentInput = CommentInput.create(commentSection.profileImageUrl);

        commentInput.hideOnFocusOut = true;
        commentInput.hideOnSubmit = true;

        inputsElement.append(commentInput.element);

        return commentInput;
      } else {
        return replyCommentInput;
      }
    }

    _showReplyCommentInput() {
      const replyCommentInput = this._getOrCreateReplyCommentInput();
      replyCommentInput.show();
      replyCommentInput.focus();
    }

    prependReply(comment) {
      const repliesElement = this.element.querySelector('.replies');
      repliesElement.prepend(comment.element);
    }

    _postLike() {
      const { commentLikesCountElement, likeButton } = this;

      ajax
        .jsonRequest('POST', this.likeUrl, {
          like: !likeButton.dataset.checked
        })
        .then(data => {
          if (data.like) {
            likeButton.dataset.checked = 'checked';
          } else {
            delete likeButton.dataset.checked;
          }

          commentLikesCountElement.innerText = data.number_of_likes;
        });
    }
  }

  Comment.className = 'comment';
  Comment.instances = new WeakMap();

  Comment.create = function create(
    id,
    username,
    profileImageUrl,
    dateString,
    message,
    likeUrl,
    liked,
    likes
  ) {
    const template = document.getElementById('comment-template');
    const element = template.content.cloneNode(true).querySelector(`.${Comment.className}`);
    element.dataset.commentId = id;
    element.dataset.likeUrl = likeUrl;
    element.querySelector('.profile').style.backgroundImage = `url('${profileImageUrl}')`;
    element.querySelector('.comment-name').innerText = username;
    element.querySelector('.comment-date').innerText = dateString;
    element.querySelector('.comment-text').innerText = message;
    element.querySelector('.comment-likes-count').innerText = likes;
    if (liked) {
      element.querySelector('.checkbox-like').dataset.checked = 'checked';
    } else {
      delete element.querySelector('.checkbox-like').dataset.checked;
    }
    return Comment.getOrWrap(element);
  };

  Comment.getOrWrap = function getOrWrap(element) {
    const c = Comment.instances.get(element);
    if (c == null) {
      return new Comment(element);
    } else {
      return c;
    }
  };

  class CommentInput {
    constructor(element) {
      CommentInput.instances.set(element, this);
      this.element = element;
      this.hideOnFocusOut = false;
      this.hideOnSubmit = false;
      this._setupEventListeners();
    }

    get formElement() {
      return this.element.querySelector('form');
    }

    get inputElement() {
      return this.element.querySelector('input');
    }

    get commentSection() {
      const commentSectionElement = this.element.closest(`.${CommentSection.className}`);
      if (commentSectionElement == null) {
        return null;
      } else {
        return CommentSection.getOrWrap(commentSectionElement);
      }
    }

    get replyTo() {
      const commentElement = this.element.closest(`.${Comment.className}`);
      if (commentElement == null) {
        return null;
      } else {
        return Comment.getOrWrap(commentElement);
      }
    }

    _setupEventListeners() {
      this.formElement.addEventListener('submit', event => {
        event.preventDefault();
        this._postComment();
      });

      this.element.addEventListener('focusout', event => {
        if (this.hideOnFocusOut && !this.element.contains(event.relatedTarget)) {
          this.hide();
        }
      });
    }

    _postComment() {
      const { commentSection, inputElement, replyTo } = this;
      const message = inputElement.value;
      inputElement.value = '';

      ajax
        .jsonRequest('POST', commentSection.commentUrl, {
          reply_to: replyTo == null ? null : replyTo.id,
          message
        })
        .then(data => {
          const comment = Comment.create(
            data.id,
            data.username,
            data.profile_image_url,
            data.date_string,
            data.message,
            data.like_url,
            data.liked,
            data.likes
          );
          if (this.hideOnSubmit) {
            this.hide();
          }

          if (replyTo == null) {
            commentSection.prependComment(comment);
          } else {
            replyTo.prependReply(comment);
          }
        });
    }

    show() {
      this.element.style.display = null;
    }

    hide() {
      this.element.style.display = 'none';
    }

    focus() {
      this.inputElement.focus();
    }
  }

  CommentInput.className = 'comment-input';
  CommentInput.instances = new WeakMap();

  CommentInput.getOrWrap = function getOrWrap(element) {
    const c = CommentInput.instances.get(element);
    if (c == null) {
      return new CommentInput(element);
    } else {
      return c;
    }
  };

  CommentInput.create = function create(profileImageUrl) {
    const template = document.getElementById('comment-input-template');
    const element = template.content.cloneNode(true).querySelector(`.${CommentInput.className}`);
    element.querySelector('.profile').style.backgroundImage = `url('${profileImageUrl}')`;
    return CommentInput.getOrWrap(element);
  };

  class CommentSection {
    constructor(element) {
      CommentSection.instances.set(element, this);
      this.element = element;
      this.commentUrl = element.dataset.commentUrl;
      this.profileImageUrl = element.dataset.profileImageUrl;
    }

    prependComment(comment) {
      this.element.querySelector('.comments').prepend(comment.element);
    }
  }

  CommentSection.className = 'comment-section';
  CommentSection.instances = new WeakMap();
  CommentSection.getOrWrap = function getOrWrap(element) {
    const c = CommentSection.instances.get(element);
    if (c == null) {
      return new CommentSection(element);
    } else {
      return c;
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    document.getElementsByClassName(CommentSection.className).forEach(CommentSection.getOrWrap);
    document.getElementsByClassName(CommentInput.className).forEach(CommentInput.getOrWrap);
    document.getElementsByClassName(Comment.className).forEach(Comment.getOrWrap);
  });

  return { CommentSection };
})();
