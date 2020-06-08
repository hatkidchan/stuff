function FloatingWindow(elem, width, height) {
    this.elem = elem;
    console.log(width, height)
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

    this.title.addEventListener('mousedown', (e) => {
        this.onDragMouseDown(e);
    });

    /*this.titlebtn.addEventListener('click', (e) => {
        if(this.elem.dataset.closed == 'true')
            this.elem.dataset.closed = 'false';
        else
            this.elem.dataset.closed = 'true';
    });*/

    document.addEventListener('mouseup', (e) => {
        if(this.is_dragging) {
            this.closeDragElement(e);
        }
    });

    document.addEventListener('mousemove', (e) => {
        if(this.is_dragging) {
            this.elementDrag(e);
        }
    });

    this.onDragMouseDown = (e) => {
        e.preventDefault();
        this.pos[2] = e.clientX;
        this.pos[3] = e.clientY;
        this.is_dragging = true;
    }

    this.elementDrag = (e) => {
        e.preventDefault();
        this.pos[0] = this.pos[2] - e.clientX;
        this.pos[1] = this.pos[3] - e.clientY;
        this.pos[2] = e.clientX;
        this.pos[3] = e.clientY;
        this.elem.style.top = (this.elem.offsetTop - this.pos[1]) + 'px';
        this.elem.style.left = (this.elem.offsetLeft - this.pos[0]) + 'px';
    }

    this.closeDragElement = (e) => {
        this.is_dragging = false;
    }

    this.setPos = (x, y) => {
        this.elem.style.left = x + 'px';
        this.elem.style.top = y + 'px';
    }
}
