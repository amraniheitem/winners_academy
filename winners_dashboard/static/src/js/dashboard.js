/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class WinnersDashboard extends Component {
    static template = "winners_dashboard.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            totalActive: 0,
            totalAlert: 0,
            totalExpired: 0,
            revenueMonth: 0,
            attendanceToday: 0,
            sessionsToday: 0,
            isLoading: true,
        });

        onWillStart(async () => {
            await this.fetchDashboardData();
        });
    }

    async fetchDashboardData() {
        this.state.isLoading = true;
        try {
            // Étudiants actifs
            this.state.totalActive = await this.orm.searchCount(
                "winners.student",
                [["status", "=", "active"]]
            );



            // Étudiants en alerte (sessions_remaining <= 2 et > 0)
            this.state.totalAlert = await this.orm.searchCount(
                "winners.student",
                [["sessions_remaining", "<=", 2], ["sessions_remaining", ">", 0]]
            );

            // Étudiants expirés (status = expired)
            this.state.totalExpired = await this.orm.searchCount(
                "winners.student",
                [["status", "=", "expired"]]
            );

            // Revenus du mois en cours (paiements confirmés)
            const now = new Date();
            const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
            const firstDayStr = firstDay.toISOString().split("T")[0];
            const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
            const lastDayStr = lastDay.toISOString().split("T")[0];

            const payments = await this.orm.readGroup(
                "winners.payment",
                [
                    ["state", "=", "confirmed"],
                    ["date", ">=", firstDayStr],
                    ["date", "<=", lastDayStr],
                ],
                ["amount:sum"],
                []
            );
            this.state.revenueMonth =
                payments.length > 0 && payments[0].amount ? payments[0].amount : 0;

            // Présences du jour
            const todayStr = now.toISOString().split("T")[0];
            this.state.attendanceToday = await this.orm.searchCount(
                "winners.attendance",
                [
                    ["date", "=", todayStr],
                    ["status", "in", ["present", "late"]],
                ]
            );

            // Séances du jour (winners.session.date is Datetime)
            const tomorrowStr = new Date(
                now.getFullYear(),
                now.getMonth(),
                now.getDate() + 1
            )
                .toISOString()
                .split("T")[0];
            this.state.sessionsToday = await this.orm.searchCount(
                "winners.session",
                [
                    ["date", ">=", todayStr],
                    ["date", "<", tomorrowStr],
                    ["status", "=", "planned"],
                ]
            );
        } catch (error) {
            console.error("Erreur chargement dashboard:", error);
        }
        this.state.isLoading = false;
    }

    async onRefresh() {
        await this.fetchDashboardData();
    }

    openStudents(statusFilter) {
        let domain = [["status", "=", statusFilter]];
        let title = "Étudiants actifs";
        if (statusFilter === "alert") {
            domain = [["sessions_remaining", "<=", 2], ["sessions_remaining", ">", 0]];
            title = "Étudiants en alerte";
        } else if (statusFilter === "expired") {
            title = "Étudiants expirés";
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: title,
            res_model: "winners.student",
            view_mode: "tree,form",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: domain,
            target: "current",
        });
    }

    openPayments() {
        const now = new Date();
        const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
        const firstDayStr = firstDay.toISOString().split("T")[0];
        const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
        const lastDayStr = lastDay.toISOString().split("T")[0];

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Paiements du mois",
            res_model: "winners.payment",
            view_mode: "tree,form",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [
                ["state", "=", "confirmed"],
                ["date", ">=", firstDayStr],
                ["date", "<=", lastDayStr],
            ],
            target: "current",
        });
    }

    openAttendance() {
        const todayStr = new Date().toISOString().split("T")[0];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Présences du jour",
            res_model: "winners.attendance",
            view_mode: "tree,form",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [["date", "=", todayStr]],
            target: "current",
        });
    }

    openSessions() {
        const now = new Date();
        const todayStr = now.toISOString().split("T")[0];
        const tomorrowStr = new Date(
            now.getFullYear(),
            now.getMonth(),
            now.getDate() + 1
        )
            .toISOString()
            .split("T")[0];

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Séances du jour",
            res_model: "winners.session",
            view_mode: "tree,form",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [
                ["date", ">=", todayStr],
                ["date", "<", tomorrowStr],
            ],
            target: "current",
        });
    }

    formatCurrency(value) {
        return new Intl.NumberFormat("fr-DZ", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value);
    }
}

registry
    .category("actions")
    .add("winners_dashboard", WinnersDashboard);
