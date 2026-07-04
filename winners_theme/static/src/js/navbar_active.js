/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";

patch(NavBar.prototype, {
    isMenuSectionActive(section) {
        const currentMenuId = this.env.services.router.current.hash.menu_id;
        if (!currentMenuId) {
            return false;
        }
        
        const checkActive = (menu) => {
            if (menu.id == currentMenuId) {
                return true;
            }
            if (menu.childrenTree) {
                return menu.childrenTree.some(checkActive);
            }
            return false;
        };
        return checkActive(section);
    }
});
