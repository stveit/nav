define(['plugins/rickshaw_graph', 'libs/spin.min'], function (RickshawGraph) {
    /*
     * GraphFetcher
     *
     * Automatically loads graphite graphs based on class attributes.
     *
     * See 'graphfetcher_controller' for global controls.
     *
     * Every graph needs the following:
     * class='graphitegraph'
     * data-url: The url of the controller returning the graph image
     *   (you need to write this controller). GraphFetcher adds a 'timeframe'
     *   parameter indicating timeframe. Valid timeframes are in the buttons
     *   list.
     * data-handler-id: If you have a button or something that shows the
     *   graph, set this to the id of that element. Otherwise the graph is
     *   loaded on page load.
     *
     * NB: Expected icon for indicating expandable is 'fa-chevron-right'
     */

    function GraphFetcher(node, urls) {
        this.checkInput(node, urls);
        this.node = node;
        this.urls = urls.split(';');
        this.lastUrlIndex = -1;
        this.urlIndex = 0;  // Index of this.urls

        this.buttons = {'day': 'Day', 'week': 'Week', 'month': 'Month', 'year': 'Year'};
        this.lastTimeFrame = '';
        this.timeframe = 'day';
        this.isOpen = false;
        this.spinner = this.createSpinner();

        this.isInitialized = false;
        var handlerId = this.node.attr('data-handler-id');
        if (handlerId) {
            this.handler = $('#' + handlerId);
            this.icon = this.handler.find('i');
            this.addToggleHandler();
        } else {
            this.init();
        }
        return this;
    }

    GraphFetcher.prototype = {
        init: function () {
            this.addButtons();
            this.loadGraph();
            this.isInitialized = true;
        },
        addToggleHandler: function () {
            var self = this;
            $(this.handler).click(function () {
                if (self.node.is(':visible')) {
                    self.close();
                } else {
                    self.open();
                }
            });
        },
        close: function () {
            this.isOpen = false;
            this.node.hide();
            this.icon.removeClass('fa-chevron-down').addClass('fa-chevron-right');
        },
        open: function () {
            if (!this.isInitialized) {
                this.init();
            }
            if (this.shouldReloadGraph()) {
                this.loadGraph();
            }
            this.node.show();
            this.isOpen = true;
            this.icon.removeClass('fa-chevron-right').addClass('fa-chevron-down');
        },
        shouldReloadGraph: function () {
            return (this.lastTimeFrame !== this.timeframe) || (this.lastUrlIndex !== this.urlIndex);
        },
        changeUrlIndex: function (index) {
            if (this.urls.length > index) {
                this.urlIndex = index;
            }
        },
        checkInput: function (node, url) {
            if (!(node instanceof jQuery && node.length)) {
                throw new Error('Need a valid node to attach to');
            }
            if (typeof url !== "string") {
                throw new Error('Need a string as url');
            }
        },
        addButtons: function () {
            var headerNode = $('<div>').appendTo(this.node);
            this.headerNode = headerNode;

            for (var key in this.buttons) {
                if (this.buttons.hasOwnProperty(key)) {
                    this.addButton(headerNode, key, this.buttons[key]);
                }
            }
            this.appendAddGraphButton();
        },
        addButton: function (node, timeframe, text) {
            var that = this;
            var button = $('<button>').addClass('tiny secondary graph-button-' + timeframe).html(text);
            button.click(function () {
                that.timeframe = timeframe;
                that.loadGraph();
            });
            button.appendTo(node);
        },
        appendAddGraphButton: function () {
            var self = this,
                button = $('<button>').addClass('tiny secondary right').text('Add graph to dashboard');
            button.click(function () {
                /* Image url is a redirect to graphite. Fetch proxy url and use
                 that as preference for graph widget */
                var url = removeURLParameter(self.graph.dataURL, 'format'),
                    headRequest = $.ajax(url, { 'type': 'HEAD' });
                headRequest.done(function (data, status, xhr) {
                    var proxyUrl = xhr.getResponseHeader('X-Where-Am-I');
                    if (proxyUrl) {
                        var request = $.post(NAV.addGraphWidgetUrl,
                            {
                                'url': removeURLParameter(proxyUrl, 'format'),
                                'target': window.location.pathname + window.location.hash
                            });
                        request.done(function () {
                            button.removeClass('secondary').addClass('success');
                        });
                        request.fail(function () {
                            button.removeClass('secondary').addClass('alert');
                        });
                    }
                });
            });
            this.headerNode.append(button);
        },
        selectButton: function() {
            $('button', this.headerNode).each(function (index, element) {
                $(element).removeClass('active');
            });
            this.node.find('button.graph-button-' + this.timeframe).addClass('active');
        },
        loadGraph: function () {
            this.lastTimeFrame = this.timeframe;
            this.lastUrlIndex = this.urlIndex;
            this.displayGraph(this.getUrl());
            this.selectButton();
        },
        displayGraph: function (url) {
            //this.spinner.spin(this.wrapper.get(0));
            var graphContainer = this.node.find('.rickshaw-container')[0];

            if (!graphContainer) {
                // If we have no container, assume old loading with images.
                var self = this;
                var image = new Image();
                image.src = url;
                image.onload = function () {
                    self.node.find('img').remove();
                    self.node.append(image);
                    self.spinner.stop();
                };
                image.onerror = function () {
                    self.wrapper.find('img').remove();
                    self.wrapper.append("<span class='alert-box alert'>Error loading image</span>");
                    self.spinner.stop();
                };
            } else {
                if (typeof this.graph === 'undefined') {
                    this.graph = new RickshawGraph(graphContainer, url);
                } else {
                    this.graph.dataURL = url;
                    this.graph.request();
                }
            }
            
        },
        getUrl: function () {
            var url = this.urls[this.urlIndex],
                escapedUrl = escapeUrl(url),
                separator = '?';
            if (url.indexOf('?') >= 0) {
                separator = '&';
            }
            return escapedUrl + separator + 'timeframe=' + this.timeframe;
        },
        createSpinner: function () {
            var options = {};  // Who knows, maybe in the future?
            return new Spinner(options);
        }
    };

    return GraphFetcher;

});

/**
 * Escape all parts of an url path.
 * @param {string} url An url or pathname to escape
 */
function escapeUrl(url) {
    return url.split('/').reduce(function(prev, curr) {
        return prev + '/' + encodeURIComponent(curr);
    });
}

function removeURLParameter(url, parameter) {
    //prefer to use l.search if you have a location/link object
    var urlparts= url.split('?');   
    if (urlparts.length>=2) {

        var prefix= encodeURIComponent(parameter)+'=';
        var pars= urlparts[1].split(/[&;]/g);

        //reverse iteration as may be destructive
        for (var i= pars.length; i-- > 0;) {    
            //idiom for string.startsWith
            if (pars[i].lastIndexOf(prefix, 0) !== -1) {  
                pars.splice(i, 1);
            }
        }

        url= urlparts[0]+'?'+pars.join('&');
        return url;
    } else {
        return url;
    }
}
