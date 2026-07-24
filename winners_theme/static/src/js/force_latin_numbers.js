/** @odoo-module **/

// Force Luxon to use Western Arabic numerals (1 2 3 4 5 6 7 8 9 0) for all dates/times across Odoo
if (window.luxon) {
    window.luxon.Settings.defaultNumberingSystem = "latn";

    if (window.luxon.DateTime && window.luxon.DateTime.prototype) {
        const origReconfigure = window.luxon.DateTime.prototype.reconfigure;
        window.luxon.DateTime.prototype.reconfigure = function (opts) {
            opts = opts || {};
            opts.numberingSystem = "latn";
            return origReconfigure.call(this, opts);
        };

        const origToFormat = window.luxon.DateTime.prototype.toFormat;
        window.luxon.DateTime.prototype.toFormat = function (fmt, opts) {
            opts = opts || {};
            opts.numberingSystem = "latn";
            return origToFormat.call(this, fmt, opts);
        };
    }
}
