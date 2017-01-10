/* This module add the "hierarchy" menu to the UI
 * This module add a div containing a selector and a scrolling tab menu
 * this module trigger graphUpdate events
 * @ Author Adrien Basso blandin
 * This module is part of regraphGui project
 * this project is under AGPL Licence
*/
define([
	"ressources/d3/d3.js",
	"ressources/simpleTree.js",
	"ressources/requestFactory.js",
	"ressources/d3/d3-context-menu.js"
	],
	function(d3,Tree,RFactory,d3ContextMenu){
	/* Create a new hierarchy module
	 * @input : container_id : the container to bind this hierarchy
	 * @input : dispatch : the dispatch event object
	 * @input : server_url : the regraph server url
	 * @return : a new Hierarchy object
	 */
	return function Hierarchy(container_id,dispatch,server_url){
		if(!server_url) throw new Error("server url undefined");
		var srv_url = server_url;//the current url of the server
		var disp = dispatch;//global dispatcher for events
		var container = d3.select("#"+container_id).append("div").attr("id","tab_menu").classed("top_menu",true);//add all tabl to menu
		var hierarchy = new Tree();//a tree containing the whole hierarchy
		var h_select = container.append("select").attr("id","h_select").classed("mod_el",true);//the hierarchy selector
		var h_list = container.append("div").attr("id","scrolling_list");//the list of son of the specified node
		var current_node = null;//the current node
		var selected_node = null;//the current selected son
		var selected_graphs = {};//the currently selected graphs
		var factory = new RFactory(srv_url);
        var right_click_menu = [
              {title : "delete",
			   action : function(elm, d, i) {
                             current_obj = hierarchy.getAbsPath(d)
			                 if (confirm("Confirmation : remove "+current_obj+" and all its children ?"))
							 	factory.delHierarchy(current_obj,function(e,r){
							 		if(e) return console.error(e);
							 		console.log(r);
							 		dispatch.call("hieUpdate",this);
							 	});
			            }

			  },
              {title : "get kappa",
			   action : toKappa
			  }
		];

		/* load a new hierarchy from the server
		 * @input : root_path : the hierarchy root pathname
		 */
		this.update = function update(root_path){
			factory.getHierarchy(root_path,function(err,req){
				hierarchy.load(req);
				current_node = hierarchy.getRoot();
				initHlist(hierarchy.getSons(current_node));
				initHselect(hierarchy.getTreePath(current_node));
			});
		};
		/* update the scrolling tab menu with the current node sons
		 * @input : data : the list of sons of the current node
		 */
		function initHlist(data){
			h_list.selectAll("*").remove();
			var slc =h_list.selectAll(".tab_menu_el")
				.data(data);
			slc.exit().remove();
			slc.enter().append("div")
				.classed("tab_menu_el",true)
				.classed("unselectable",true)
				.classed("selected",false)
				.attr("id",function(d){return d})
				.on("click",function(d,i){return dispach_click(d,i,this)})
				.on("contextmenu",d3ContextMenu(right_click_menu))
				.on("dblclick",function(d){return lvlChange(d)})
				.text(function(d){
					let nm = hierarchy.getName(d);
					return nm.length>14?nm.substring(0,12).concat("..."):nm;
				});
		};
		/* update the selector with the current node parents
		 * @input : data : the absolute path of the current node
		 */
		function initHselect(data){
			h_select.selectAll("*").remove();
			h_select.selectAll("option")
				.data(data)
				.enter().append("option")
					.text(function(d){return hierarchy.getName(d)})
					.attr("selected",function(d){return d==current_node});
			h_select.on("change",lvlChange);
				
		};

		function dispach_click(d,i,elem){
		    d3.event.stopPropagation();
			if(d3.event.ctrlKey){
				if(d3.select(elem).classed("selected"))
					d3.select(elem).classed("selected",false);
				else 
					d3.select(elem).classed("selected",true);
			}
			else{
				tabChange(d,elem);
			}
			
		};
		/* color in blue the currently selected node of the scrolling tab menu
		 * @input : id : the new selected node
		 * @call : graphUpdate event
		 */
		function tabChange(id,elem){
			if(selected_node==id)return;
			selected_node = id;
			// h_list.selectAll(".tab_menu_el")
			// 	.style("color","rgb(251, 249, 200)")//show the correct menu element
			// 	.style("background",function(d){
			// 		return d==id?"linear-gradient(to bottom, #3fa4f0 0%, #0f71ba 100%)":"none";
			// 	});

			h_list.selectAll(".tab_menu_el")
			      .classed("current",false)
			d3.select(elem)
			      .classed("current",true)	  
			disp.call("graphUpdate",this,hierarchy.getAbsPath(id));
			disp.call(
				"tabUpdate",
				this,
				hierarchy.getAbsPath(id),
				hierarchy.getSons(current_node).map(function(d){
					return hierarchy.getName(d);
				}),
				hierarchy.getAbsPath(current_node),
				"hierarchy"
			);
		};
		/* change the current node in the hierarchy
		 * this function update the selector and the tab menu
		 * @input : id : the new current node
		 */
		function lvlChange(id){
			d3.event.stopPropagation();
			var data = id;
			if(!id){
				var si   = h_select.property('selectedIndex'),
				s    = h_select.selectAll("option").filter(function (d, i) { return i === si });
				data = s.datum();
			}
			if(hierarchy.getSons(data).length==0)return;
			current_node = data;
			initHlist(hierarchy.getSons(data));
			initHselect(hierarchy.getTreePath(data));
		};

		/* Convert the current graph into kappa : TODO
		 * Open a new page with the Kappa code 
		 */
		function toKappa(){
            callback = function(error, response){
				if(error) {
					alert(error.currentTarget.response);
				    return false;
				}
                d3.select("#json_link")
                  .attr("href",
                             'data:text/json;charset=utf-8,'
							  + encodeURIComponent(JSON.parse(response.response)["kappa_code"]));
                document.getElementById('json_link').click();
                       };
			nugget_list = []		   
			d3.selectAll(".tab_menu_el.selected")
			                .each(function(){
								nugget_list.push(hierarchy.getName(this.id))
							})
			path = hierarchy.getAbsPath(current_node)+"/"
			path = (path == "//")?"/":path
            factory.getKappa(path, JSON.stringify({"names": nugget_list}), callback)
            return false;
		};
	};
});
