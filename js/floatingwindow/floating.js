function FloatingWindow(elem, width, height) {
    this.elem = elem;
    this.elem.style.width = width + 'px';
    this.elem.style.height = (height + 20) + 'px';
    this.title = elem.getElementsByTagName('div')[0];
    this.title.style.width = width + 'px';
    //this.titlebtn = this.title.getElementsByTagName('div')[0];
    this.content = elem.getElementsByTagName('div')[1];
    this.content.style.width = width + 'px';
    this.content.style.height = height + 'px';
    this.now_dragging = false;
    this.pos = [0, 0, 0, 0];
    var self = this;

    this.title.addEventListener('mousedown', function(e) {
        self.onDragMouseDown(e);
    });

    this.title.addEventListener('touchstart', function(e) {
        self.onDragMouseDown(e.changedTouches[0], true);
    });
  
    /*this.titlebtn.addEventListener('click', (e) => {
        if(this.elem.dataset.closed == 'true')
            this.elem.dataset.closed = 'false';
        else
            this.elem.dataset.closed = 'true';
    });*/

    document.addEventListener('mouseup', function(e) {
        if(self.is_dragging) {
            self.closeDragElement(e);
        }
    });

    document.addEventListener('touchend', function(e) {
        if(self.is_dragging) {
            self.closeDragElement(e.changedTouches[0], true);
        }
    });

    document.addEventListener('mousemove', function(e) {
        if(self.is_dragging) {
            self.elementDrag(e);
        }
    });

    document.addEventListener('touchmove', function(e) {
        if(self.is_dragging) {
            self.elementDrag(e.changedTouches[0], true);
        }
    });

    this.onDragMouseDown = function(e, isTouch) {
        if(!isTouch) e.preventDefault();
        self.pos[2] = e.clientX;
        self.pos[3] = e.clientY;
        self.is_dragging = true;
    }

    this.elementDrag = function(e, isTouch) {
        if(!isTouch) e.preventDefault();
        self.pos[0] = self.pos[2] - e.clientX;
        self.pos[1] = self.pos[3] - e.clientY;
        self.pos[2] = e.clientX;
        self.pos[3] = e.clientY;
        self.elem.style.top = (self.elem.offsetTop - self.pos[1]) + 'px';
        self.elem.style.left = (self.elem.offsetLeft - self.pos[0]) + 'px';
    }

    this.closeDragElement = function(e) {
        self.is_dragging = false;
    }

    this.setPos = function(x, y) {
        self.elem.style.left = x + 'px';
        self.elem.style.top = y + 'px';
    }
}
