/* global ajax:false */

window.comments = (function comments() {
  class Comment {
    constructor(element) {
      this.id = element.dataset.commentId;
      this.likeUrl = element.dataset.likeUrl;
      this.editUrl = element.dataset.editUrl;
      this.deleteUrl = element.dataset.deleteUrl;
      this.profileImageUrl = element.dataset.profileImageUrl;
      this.element = element;
      this._setupEventListeners();
    }

    get replyLink() {
      return this.element.querySelector('.comment-reply');
    }

    get editLink() {
      return this.element.querySelector('.comment-edit');
    }

    get deleteLink() {
      return this.element.querySelector('.comment-delete');
    }

    get likeButton() {
      return this.element.querySelector('.checkbox-like');
    }

    get commentLikesCountElement() {
      return this.element.querySelector('.comment-likes-count');
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
      this.replyLink.addEventListener('click', event => {
        event.preventDefault();
        this._showReplyInput();
      });

      this.editLink.addEventListener('click', event => {
        event.preventDefault();
        this._showEditInput();
      });

      this.deleteLink.addEventListener('click', event => {
        event.preventDefault();
        this._postDeleteComment();
      });

      this.likeButton.addEventListener('click', this._postLike.bind(this));
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
      const { commentSection, replyInput, replyInputsElement } = this;
      if (replyInput == null) {
        const replyInput = ReplyInput.create(commentSection.profileImageUrl);
        replyInputsElement.append(replyInput.element);
        return replyInput;
      } else {
        return replyInput;
      }
    }

    _showReplyInput() {
      const replyInput = this._getOrCreateReplyInput();
      replyInput.show();
      replyInput.focus();
    }

    prependReply(comment) {
      const repliesElement = this.element.querySelector('.replies .comments');
      repliesElement.prepend(comment.element);
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
      const { profileImageUrl, editInput, editInputsElement } = this;
      if (editInput == null) {
        const editInput = EditInput.create(profileImageUrl);
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

    _postDeleteComment() {
      const { deleteUrl, element } = this;

      ajax.jsonRequest('POST', deleteUrl).then(() => {
        element.remove();
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
    likeUrl,
    liked,
    likes,
    editUrl,
    deleteUrl
  ) {
    // console.log('id: ', id, 'profileImageUrl: ', profileImageUrl, 'msg: ', message)
    const template = document.getElementById('comment-template');
    const element = template.content.cloneNode(true).querySelector(`.${Comment.className}`);
    element.dataset.commentId = id;
    element.dataset.profileImageUrl = profileImageUrl;
    element.dataset.likeUrl = likeUrl;
    element.dataset.editUrl = editUrl;
    element.dataset.deleteUrl = deleteUrl;
    element.querySelector('.profile').style.backgroundImage = `url('${profileImageUrl}')`;
    element.querySelector('.comment-name').innerText = fullName;
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
      this.element = element;
    }

    get formElement() {
      return this.element.querySelector('form');
    }

    get inputElement() {
      return this.element.querySelector('input');
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
      this.formElement.addEventListener('submit', event => {
        event.preventDefault();
        this._postComment();
      });
    }

    _postComment() {
      const { commentSection, inputElement } = this;
      const message = inputElement.value;
      if (message === '') {
        return
      }

      inputElement.value = '';

      ajax
        .jsonRequest('POST', commentSection.commentUrl, {
          reply_to: null,
          message
        })
        .then(data => {
          const comment = Comment.create(
            data.id,
            data.full_name,
            data.profile_image_url,
            data.date_string,
            data.message,
            data.like_url,
            data.liked,
            data.likes,
            data.edit_url,
            data.delete_url
          );
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
      this.formElement.addEventListener('submit', event => {
        event.preventDefault();
        this.hide();
        this._postReply();
      });

      this.element.addEventListener('focusout', event => {
        if (!this.element.contains(event.relatedTarget)) {
          this.hide();
        }
      });
    }

    _postReply() {
      const { commentSection, inputElement, replyTo } = this;
      const message = inputElement.value;
      inputElement.value = '';

      ajax
        .jsonRequest('POST', commentSection.commentUrl, {
          reply_to: replyTo.id,
          message
        })
        .then(data => {
          const comment = Comment.create(
            data.id,
            data.full_name,
            data.profile_image_url,
            data.date_string,
            data.message,
            data.like_url,
            data.liked,
            data.likes,
            data.edit_url,
            data.delete_url
          );
          replyTo.prependReply(comment);
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
    element.querySelector('.profile').style.backgroundImage = `url('${profileImageUrl}')`;
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
      this.inputElement.value = this.comment.message;
    }

    _setupEventListeners() {
      this.formElement.addEventListener('submit', event => {
        event.preventDefault();
        this.comment.showContent();
        this.hide();
        this._postEdit();
      });

      this.element.addEventListener('focusout', event => {
        if (!this.element.contains(event.relatedTarget)) {
          this.comment.showContent();
          this.hide();
        }
      });
    }

    _postEdit() {
      const { comment, inputElement } = this;
      const message = inputElement.value;
      inputElement.value = '';

      ajax
        .jsonRequest('POST', comment.editUrl, {
          message
        })
        .then(data => {
          this.comment.message = data.message;
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
    element.querySelector('.profile').style.backgroundImage = `url('${profileImageUrl}')`;
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

  document.addEventListener('DOMContentLoaded', () => {
    document.getElementsByClassName(Section.className).forEach(Section.getOrWrap);
    document.getElementsByClassName(MainInput.className).forEach(MainInput.getOrWrap);
    document.getElementsByClassName(ReplyInput.className).forEach(ReplyInput.getOrWrap);
    document.getElementsByClassName(EditInput.className).forEach(EditInput.getOrWrap);
    document.getElementsByClassName(Comment.className).forEach(Comment.getOrWrap);
  });

  return { CommentSection: Section };
})();
