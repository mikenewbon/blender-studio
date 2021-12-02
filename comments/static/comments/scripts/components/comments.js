/* eslint-disable no-unused-expressions */
/* global ajax:false */

window.comments = (function comments() {
  class Comment {
    constructor(element) {
      this.id = element.dataset.commentId;
      this.likeUrl = element.dataset.commentLikeUrl;
      this.editUrl = element.dataset.editUrl;
      this.deleteUrl = element.dataset.deleteUrl;
      this.deleteTreeUrl = element.dataset.deleteTreeUrl;
      this.hardDeleteTreeUrl = element.dataset.hardDeleteTreeUrl;
      this.archiveUrl = element.dataset.archiveUrl;
      this.profileImageUrl = element.dataset.profileImageUrl;
      this.message_markdown = element.dataset.message;
      this.message_html = element.querySelector('.comment-text').innerHTML;
      this.element = element;
      this._setupEventListeners();
    }

    get replyLink() {
      return this.element.querySelector('.comment-reply');
    }

    get editLink() {
      return this.element.querySelector(':scope > .comment-content .comment-edit');
    }

    get deleteLink() {
      return this.element.querySelector('.comment-delete');
    }

    get deleteTreeLink() {
      return this.element.querySelector('.comment-delete-tree');
    }

    get hardDeleteTreeLink() {
      return this.element.querySelector('.comment-hard-delete-tree');
    }

    get archiveLink() {
      return this.element.querySelector('.comment-archive');
    }

    get likeButton() {
      return this.element.querySelector('.checkbox-like');
    }

    get commentLikesCountElement() {
      return this.element.querySelector('.likes-count');
    }

    get commentSection() {
      const commentSectionElement = this.element.closest(`.${Section.className}`);
      if (commentSectionElement == null) {
        return null;
      } else {
        return Section.getOrWrap(commentSectionElement);
      }
    }

    get textElement() {
      return this.element.querySelector('.comment-text');
    }

    get message() {
      return this.textElement.innerText;
    }

    set message(value) {
      this.textElement.innerText = value;
    }

    _setupEventListeners() {
      this.replyLink &&
        this.replyLink.addEventListener('click', (event) => {
          event.preventDefault();
          this._showReplyInput();
        });

      this.editLink &&
        this.editLink.addEventListener('click', (event) => {
          event.preventDefault();
          this._showEditInput();
        });

      this.deleteLink &&
        this.deleteLink.addEventListener('click', (event) => {
          event.preventDefault();
          this._postDeleteComment();
        });

      this.deleteTreeLink &&
        this.deleteTreeLink.addEventListener('click', (event) => {
          event.preventDefault();
          this._postDeleteTreeComment();
        });

      this.hardDeleteTreeLink &&
        this.hardDeleteTreeLink.addEventListener('click', (event) => {
          event.preventDefault();
          this._postHardDeleteTreeComment();
        });

      this.archiveLink &&
        this.archiveLink.addEventListener('click', (event) => {
          event.preventDefault();
          this._postArchiveComment();
        });

      this.likeButton && this.likeButton.addEventListener('click', this._postLike.bind(this));
    }

    get replyInputsElement() {
      const inputsElement = this.element.querySelector('.comment-reply-inputs');

      if (inputsElement == null) {
        return null;
      } else {
        return inputsElement;
      }
    }

    get replyInput() {
      const { replyInputsElement } = this;
      if (replyInputsElement == null) {
        return null;
      }

      const replyInputElement = replyInputsElement.querySelector(`.${ReplyInput.className}`);
      if (replyInputElement == null) {
        return null;
      }

      return ReplyInput.getOrWrap(replyInputElement);
    }

    _getOrCreateReplyInput() {
      const { replyInput, replyInputsElement } = this;
      let inputText = null;
      if (replyInput == null) {
        // eslint-disable-next-line no-undef
        const replyInput = ReplyInput.create(currentUser.image_url);
        inputText = `@${this.element.querySelector('.comment-name').innerText}&nbsp;`;
        replyInput.element.querySelector('.comment-input-div').innerHTML = inputText;
        replyInputsElement.append(replyInput.element);
        return replyInput;
      } else {
        inputText = `@${this.element.querySelector('.comment-name').innerText}&nbsp;`;
        replyInput.element.querySelector('.comment-input-div').innerHTML = inputText;
        return replyInput;
      }
    }

    _showReplyInput() {
      const replyInput = this._getOrCreateReplyInput();
      const replyInputElement = replyInput.element.querySelector('.comment-input-div');
      replyInput.show();
      replyInputElement.focus();
      // Set caret to the end.
      const range = document.createRange();
      const sel = window.getSelection();
      range.setStart(replyInputElement.firstChild, replyInputElement.innerText.length);
      range.collapse(true);
      sel.removeAllRanges();
      sel.addRange(range);
    }

    appendReply(comment) {
      const repliesElement = this.element
        .closest('.top-level-comment')
        .querySelector('.replies .comments');
      repliesElement.append(comment.element);
    }

    get editInputsElement() {
      const inputsElement = this.element.querySelector('.comment-edit-inputs');

      if (inputsElement == null) {
        return null;
      } else {
        return inputsElement;
      }
    }

    get editInput() {
      const { editInputsElement } = this;
      if (editInputsElement == null) {
        return null;
      }

      const editInputElement = editInputsElement.querySelector(`.${EditInput.className}`);
      if (editInputElement == null) {
        return null;
      }

      return EditInput.getOrWrap(editInputElement);
    }

    _getOrCreateEditInput() {
      const { editInput, editInputsElement } = this;
      if (editInput == null) {
        // eslint-disable-next-line no-undef
        const editInput = EditInput.create(currentUser.image_url);
        editInputsElement.append(editInput.element);
        return editInput;
      } else {
        return editInput;
      }
    }

    _showEditInput() {
      const editInput = this._getOrCreateEditInput();
      editInput.prepopulateMessage();
      this.hideContent();
      editInput.show();
      editInput.focus();
    }

    _postLike() {
      const { likeButton } = this;

      ajax
        .jsonRequest('POST', this.likeUrl, {
          like: !likeButton.dataset.checked,
        })
        .then((data) => {
          if (data.like) {
            likeButton.dataset.checked = 'checked';
          } else {
            delete likeButton.dataset.checked;
          }

          if (likeButton.querySelector('.likes-count')) {
            // eslint-disable-next-line no-param-reassign
            likeButton.querySelector('.likes-count').innerText = data.number_of_likes;
          } else {
            const likeCountHTML = `<span class="likes-count">${data.number_of_likes}</span>`;
            likeButton.insertAdjacentHTML('beforeend', likeCountHTML);
          }
        });
    }

    _postDeleteComment() {
      const { deleteUrl, element } = this;

      ajax.jsonRequest('POST', deleteUrl).then(() => {
        element.querySelector('.comment-text').textContent = '[deleted]';
        element.querySelector('.comment-name').textContent = '[deleted]';

        const commentToolbar = element.querySelector('.comment-toolbar');
        // eslint-disable-next-line no-unused-expressions
        commentToolbar && commentToolbar.remove();
      });
    }

    _postDeleteTreeComment() {
      const { deleteTreeUrl, element } = this;

      ajax.jsonRequest('POST', deleteTreeUrl).then(() => {
        if (element.classList.contains('.top-level-comment')) {
          // eslint-disable-next-line no-return-assign
          element.querySelectorAll('.comment-text').forEach((e) => (e.textContent = '[deleted]'));
          // eslint-disable-next-line no-return-assign
          element.querySelectorAll('.comment-name').forEach((e) => (e.textContent = '[deleted]'));
          // eslint-disable-next-line no-unused-expressions
          element.querySelector('.comment-toolbar') &&
            element.querySelectorAll('.comment-toolbar').forEach((e) => e.remove());
        } else {
          element
            .closest('.top-level-comment')
            .querySelectorAll('.comment-text')
            // eslint-disable-next-line no-return-assign
            .forEach((e) => (e.textContent = '[deleted]'));
          element
            .closest('.top-level-comment')
            .querySelectorAll('.comment-name')
            // eslint-disable-next-line no-return-assign
            .forEach((e) => (e.textContent = '[deleted]'));
        }
      });
    }

    _postHardDeleteTreeComment() {
      const { hardDeleteTreeUrl, element } = this;

      ajax.jsonRequest('POST', hardDeleteTreeUrl).then(() => {
        if (element.classList.contains('.top-level-comment')) {
          element.remove();
        } else {
          element.closest('.top-level-comment').remove();
        }
      });
    }

    _postArchiveComment() {
      const { archiveUrl, element } = this;
      const archivedBadge = '<p class="badge bg-secondary archived-badge">Archived</p>';
      // const commentTitleBar = element.querySelectorAll('.comment-name-date-wrapper');

      function unarchive(element) {
        element.classList.remove('archived');
        element.querySelectorAll('.comment').forEach((e) => e.classList.remove('archived'));
        element
          .querySelectorAll('.comment-archive .material-icons')
          // eslint-disable-next-line no-return-assign
          .forEach((e) => (e.textContent = 'archive'));
        element
          .querySelectorAll('.comment-archive-text')
          // eslint-disable-next-line no-return-assign
          .forEach((e) => (e.textContent = 'Archive comment'));
        element.querySelectorAll('.archived-badge').forEach((e) => e.remove());
        // eslint-disable-next-line no-unused-expressions
        element.querySelector('.comment-expand-archived') &&
          element.querySelectorAll('.comment-expand-archived').forEach((e) => e.remove());
      }

      function archive(element) {
        element.classList.add('archived');
        element.querySelectorAll('.comment').forEach((e) => e.classList.add('archived'));
        element
          .querySelectorAll('.comment-archive .material-icons')
          // eslint-disable-next-line no-return-assign
          .forEach((e) => (e.textContent = 'unarchive'));
        element
          .querySelectorAll('.comment-archive-text')
          // eslint-disable-next-line no-return-assign
          .forEach((e) => (e.textContent = 'Un-archive comment'));
        element
          .querySelectorAll('.comment-name-date-wrapper')
          // eslint-disable-next-line no-return-assign
          .forEach((e) => (e.innerHTML += archivedBadge));
      }

      ajax.jsonRequest('POST', archiveUrl).then(() => {
        if (element.classList.contains('archived')) {
          if (element.classList.contains('top-level-comment')) {
            unarchive(element);
          } else {
            unarchive(element.closest('.top-level-comment'));
          }
        } else if (element.classList.contains('top-level-comment')) {
          archive(element);
        } else {
          archive(element.closest('.top-level-comment'));
        }
      });
    }

    get contentElement() {
      return this.element.querySelector('.comment-content');
    }

    showContent() {
      this.contentElement.style.display = null;
    }

    hideContent() {
      this.contentElement.style.display = 'none';
    }
  }

  Comment.className = 'comment';
  Comment.instances = new WeakMap();

  Comment.create = function create(
    id,
    fullName,
    profileImageUrl,
    dateString,
    message,
    messageHtml,
    likeUrl,
    liked,
    likes,
    editUrl,
    deleteUrl,
    archiveUrl
  ) {
    const template = document.getElementById('comment-template');
    const element = template.content.cloneNode(true).querySelector(`.${Comment.className}`);
    element.dataset.commentId = id;
    element.dataset.profileImageUrl = profileImageUrl;
    element.dataset.commentLikeUrl = likeUrl;
    element.dataset.editUrl = editUrl;
    element.dataset.deleteUrl = deleteUrl;
    element.dataset.archiveUrl = archiveUrl;
    element.dataset.message = message;
    if (profileImageUrl) {
      element.querySelector('.profile').style.backgroundImage = `url('${profileImageUrl}')`;
    }
    element.querySelector('.comment-name').innerText = fullName;
    element.querySelector('.comment-date').innerText = dateString;
    element.querySelector('.comment-text').innerHTML = messageHtml;
    element.querySelector('.likes-count').innerText = likes;
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
      this.element = element;
    }

    get sendButton() {
      return this.element.querySelector('.comment-send .btn-input');
    }

    get inputElement() {
      return this.element.querySelector('.comment-input-div');
    }

    get commentSection() {
      const commentSectionElement = this.element.closest(`.${Section.className}`);
      if (commentSectionElement == null) {
        return null;
      } else {
        return Section.getOrWrap(commentSectionElement);
      }
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

  class MainInput extends CommentInput {
    constructor(element) {
      super(element);
      MainInput.instances.set(element, this);
      this._setupEventListeners();
    }

    _setupEventListeners() {
      this.sendButton.addEventListener('click', (event) => {
        event.preventDefault();
        this._postComment();
      });

      this.inputElement.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
          event.preventDefault();
          this.sendButton.click();
        } else if (event.key === 'Escape') {
          this.comment.showContent();
          this.hide();
        }
      });
    }

    _postComment() {
      const { commentSection, inputElement } = this;
      const message = inputElement.innerText;

      if (message === '') {
        return;
      }

      inputElement.innerText = '';
      ajax
        .jsonRequest('POST', commentSection.commentUrl, {
          reply_to: null,
          message,
        })
        .then((data) => {
          const comment = Comment.create(
            data.id,
            data.full_name,
            data.profile_image_url,
            data.date_string,
            data.message,
            data.message_html,
            data.like_url,
            data.liked,
            data.likes,
            data.edit_url,
            data.delete_url
          );
          comment.element.classList.add('top-level-comment');
          commentSection.prependComment(comment);
        });
    }
  }

  MainInput.className = 'comment-main-input';
  MainInput.instances = new WeakMap();

  MainInput.getOrWrap = function getOrWrap(element) {
    const c = MainInput.instances.get(element);
    if (c == null) {
      return new MainInput(element);
    } else {
      return c;
    }
  };

  class ReplyInput extends CommentInput {
    constructor(element) {
      super(element);
      ReplyInput.instances.set(element, this);
      this._setupEventListeners();
    }

    get replyTo() {
      return Comment.getOrWrap(this.element.closest(`.${Comment.className}`));
    }

    _setupEventListeners() {
      this.sendButton.addEventListener('click', (event) => {
        event.preventDefault();
        this._postReply();
        this.hide();
      });

      this.inputElement.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
          event.preventDefault();
          this.sendButton.click();
        } else if (event.key === 'Escape') {
          // this.comment.showContent();
          this.hide();
        }
      });
    }

    _postReply() {
      const { commentSection, inputElement, replyTo } = this;

      const message = inputElement.innerText;

      inputElement.innerText = '';

      ajax
        .jsonRequest('POST', commentSection.commentUrl, {
          reply_to: replyTo.id,
          message,
        })
        .then((data) => {
          const comment = Comment.create(
            data.id,
            data.full_name,
            data.profile_image_url,
            data.date_string,
            data.message,
            data.message_html,
            data.like_url,
            data.liked,
            data.likes,
            data.edit_url,
            data.delete_url
          );
          replyTo.appendReply(comment);
        });
    }
  }

  ReplyInput.className = 'comment-reply-input';
  ReplyInput.instances = new WeakMap();

  ReplyInput.getOrWrap = function getOrWrap(element) {
    const c = ReplyInput.instances.get(element);
    if (c == null) {
      return new ReplyInput(element);
    } else {
      return c;
    }
  };

  ReplyInput.create = function create(profileImageUrl) {
    const template = document.getElementById('comment-reply-input-template');
    const element = template.content.cloneNode(true).querySelector(`.${ReplyInput.className}`);
    if (!profileImageUrl) {
      element.querySelector('.profile').style.backgroundImage = `url('${profileImageUrl}')`;
    }
    return ReplyInput.getOrWrap(element);
  };

  class EditInput extends CommentInput {
    constructor(element) {
      super(element);
      EditInput.instances.set(element, this);
      this._setupEventListeners();
    }

    get comment() {
      return Comment.getOrWrap(this.element.closest(`.${Comment.className}`));
    }

    prepopulateMessage() {
      this.inputElement.innerText = this.comment.message_markdown;
    }

    _setupEventListeners() {
      this.sendButton.addEventListener('click', (event) => {
        event.preventDefault();
        this.comment.showContent();
        this._postEdit();
        this.hide();
      });

      this.inputElement.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
          event.preventDefault();
          this.sendButton.click();
        } else if (event.key === 'Escape') {
          this.comment.showContent();
          this.hide();
        }
      });
    }

    _postEdit() {
      const { comment, inputElement } = this;
      const message = inputElement.innerText;

      inputElement.innerText = '';
      ajax
        .jsonRequest('POST', comment.editUrl, {
          message,
        })
        .then((data) => {
          this.comment.message = data.message;
          this.comment.element.dataset.message = this.comment.message;
          this.comment.message_html = data.message_html;
          this.comment.element.querySelector('.comment-text').innerHTML = data.message_html;
        });
    }
  }

  EditInput.className = 'comment-edit-input';
  EditInput.instances = new WeakMap();

  EditInput.getOrWrap = function getOrWrap(element) {
    const c = EditInput.instances.get(element);
    if (c == null) {
      return new EditInput(element);
    } else {
      return c;
    }
  };

  EditInput.create = function create(profileImageUrl) {
    const template = document.getElementById('comment-edit-input-template');
    const element = template.content.cloneNode(true).querySelector(`.${EditInput.className}`);
    if (!profileImageUrl) {
      element.querySelector('.profile').style.backgroundImage = `url('${profileImageUrl}')`;
    }
    return EditInput.getOrWrap(element);
  };

  class Section {
    constructor(element) {
      Section.instances.set(element, this);
      this.element = element;
      this.commentUrl = element.dataset.commentUrl;
      this.profileImageUrl = element.dataset.profileImageUrl;
    }

    prependComment(comment) {
      this.element.querySelector('.comments').prepend(comment.element);
    }
  }

  Section.className = 'comment-section';
  Section.instances = new WeakMap();
  Section.getOrWrap = function getOrWrap(element) {
    const c = Section.instances.get(element);
    if (c == null) {
      return new Section(element);
    } else {
      return c;
    }
  };

  // Comment actions are activated on 'activateComments' event. This allows to activate
  // comments manually if needed. Normally the event is dispatched after DOM loads.
  document.addEventListener('DOMContentLoaded', () => {
    const event = new CustomEvent('activateComments', { bubbles: true });
    document.dispatchEvent(event);
  });

  document.addEventListener('activateComments', () => {
    document.getElementsByClassName(Section.className).forEach(Section.getOrWrap);
    document.getElementsByClassName(MainInput.className).forEach(MainInput.getOrWrap);
    document.getElementsByClassName(ReplyInput.className).forEach(ReplyInput.getOrWrap);
    document.getElementsByClassName(EditInput.className).forEach(EditInput.getOrWrap);
    document.getElementsByClassName(Comment.className).forEach(Comment.getOrWrap);
  });

  return { CommentSection: Section };
})();
