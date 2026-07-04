/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";

class WinnersDashboard extends Component {
    static template = "winners_dashboard.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.user = useService("user");

        // Refs for charts
        this.revenueChartRef = useRef("revenueChart");
        this.studentChartRef = useRef("studentChart");

        this.state = useState({
            isLoading: true,
            isSuperAdmin: false,
            branches: [],
            selectedBranchId: "all",

            // 1. Students KPIs
            totalStudents: 0,
            totalActive: 0,
            totalAlert: 0,
            totalExpired: 0,
            newStudentsMonth: 0,

            // 2. Financial KPIs
            revenueMonth: 0,
            avgPaymentAmount: 0,
            totalConfirmedPayments: 0,

            // 3. Teachers & Classes KPIs
            totalTeachers: 0,
            totalGroups: 0,

            // 4. Rooms & Schedules KPIs
            totalRooms: 0,
            sessionsToday: 0,
            attendanceToday: 0,

            // 5. Recent Lists
            recentPayments: [],
            todaySessions: [],

            // Chart values
            chartData: {
                revenue: { labels: [], values: [] }
            }
        });

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            this.state.isSuperAdmin = await this.user.hasGroup(
                "winners_auth.winners_group_super_admin"
            );
            if (this.state.isSuperAdmin) {
                this.state.branches = await this.orm.searchRead(
                    "winners.branch",
                    [],
                    ["id", "name"]
                );
            }
            await this.fetchDashboardData();
        });

        onMounted(() => {
            this.renderCharts();
        });
    }

    async fetchDashboardData() {
        this.state.isLoading = true;
        try {
            // Base domain for branch filtering
            const baseDomain = [];
            if (this.state.selectedBranchId !== "all") {
                baseDomain.push(["branch_id", "=", parseInt(this.state.selectedBranchId)]);
            }

            // ------------------------------------------
            // 1. STUDENTS METRICS
            // ------------------------------------------
            this.state.totalActive = await this.orm.searchCount("winners.student", [...baseDomain, ["status", "=", "active"]]);
            this.state.totalAlert = await this.orm.searchCount("winners.student", [...baseDomain, ["sessions_remaining", "<=", 2], ["sessions_remaining", ">", 0]]);
            this.state.totalExpired = await this.orm.searchCount("winners.student", [...baseDomain, ["status", "=", "expired"]]);
            this.state.totalStudents = this.state.totalActive + this.state.totalAlert + this.state.totalExpired;

            const now = new Date();
            const firstDayOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
            const firstDayOfMonthStr = firstDayOfMonth.toISOString().split("T")[0];
            this.state.newStudentsMonth = await this.orm.searchCount("winners.student", [...baseDomain, ["create_date", ">=", firstDayOfMonthStr]]);

            // ------------------------------------------
            // 2. FINANCIAL METRICS
            // ------------------------------------------
            const firstDayStr = firstDayOfMonthStr;
            const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
            const lastDayStr = lastDay.toISOString().split("T")[0];

            const payments = await this.orm.readGroup(
                "winners.payment",
                [
                    ...baseDomain,
                    ["state", "=", "confirmed"],
                    ["date", ">=", firstDayStr],
                    ["date", "<=", lastDayStr],
                ],
                ["amount:sum", "amount:avg", "id:count"],
                []
            );

            if (payments.length > 0) {
                this.state.revenueMonth = payments[0].amount ? payments[0].amount : 0;
                this.state.avgPaymentAmount = payments[0].amount ? (payments[0].amount / (payments[0].id_count || 1)) : 0;
                this.state.totalConfirmedPayments = payments[0].id_count || 0;
            } else {
                this.state.revenueMonth = 0;
                this.state.avgPaymentAmount = 0;
                this.state.totalConfirmedPayments = 0;
            }

            // ------------------------------------------
            // 3. TEACHERS & GROUPS
            // ------------------------------------------
            this.state.totalTeachers = await this.orm.searchCount("winners.teacher", baseDomain);
            this.state.totalGroups = await this.orm.searchCount("winners.group", baseDomain);

            // ------------------------------------------
            // 4. ROOMS & SESSIONS
            // ------------------------------------------
            this.state.totalRooms = await this.orm.searchCount("winners.room", baseDomain);

            const todayStr = now.toISOString().split("T")[0];
            const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
            const tomorrowStr = tomorrow.toISOString().split("T")[0];

            this.state.sessionsToday = await this.orm.searchCount(
                "winners.session",
                [
                    ...baseDomain,
                    ["date", ">=", todayStr],
                    ["date", "<", tomorrowStr],
                    ["status", "=", "planned"],
                ]
            );

            this.state.attendanceToday = await this.orm.searchCount(
                "winners.attendance",
                [
                    ...baseDomain,
                    ["date", "=", todayStr],
                    ["status", "in", ["present", "late"]],
                ]
            );

            // ------------------------------------------
            // 5. RECENT LISTS (LAST 5 RECORD VALUES)
            // ------------------------------------------
            this.state.recentPayments = await this.orm.searchRead(
                "winners.payment",
                baseDomain,
                ["id", "student_id", "date", "amount", "state"],
                { limit: 5, order: "date desc, id desc" }
            );

            this.state.todaySessions = await this.orm.searchRead(
                "winners.session",
                [...baseDomain, ["date", ">=", todayStr], ["date", "<", tomorrowStr]],
                ["id", "group_id", "teacher_id", "room_id", "date", "status"],
                { limit: 5, order: "date asc" }
            );

            // ------------------------------------------
            // 6. CHART DATA (LAST 6 MONTHS REVENUE)
            // ------------------------------------------
            const sixMonthsAgo = new Date();
            sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 5);
            sixMonthsAgo.setDate(1);
            const sixMonthsAgoStr = sixMonthsAgo.toISOString().split("T")[0];

            const recentPaymentsData = await this.orm.searchRead(
                "winners.payment",
                [...baseDomain, ["state", "=", "confirmed"], ["date", ">=", sixMonthsAgoStr]],
                ["date", "amount"]
            );

            const months = ["Janv", "Févr", "Mars", "Avril", "Mai", "Juin", "Juil", "Août", "Sept", "Oct", "Nov", "Déc"];
            const revenueByMonth = {};
            
            for (let i = 5; i >= 0; i--) {
                const d = new Date();
                d.setMonth(d.getMonth() - i);
                const mLabel = months[d.getMonth()] + " " + d.getFullYear().toString().substr(-2);
                revenueByMonth[mLabel] = 0;
            }

            recentPaymentsData.forEach(p => {
                if (p.date && p.amount) {
                    const pDate = new Date(p.date);
                    const mLabel = months[pDate.getMonth()] + " " + pDate.getFullYear().toString().substr(-2);
                    if (mLabel in revenueByMonth) {
                        revenueByMonth[mLabel] += p.amount;
                    }
                }
            });

            this.state.chartData.revenue.labels = Object.keys(revenueByMonth);
            this.state.chartData.revenue.values = Object.values(revenueByMonth);

        } catch (error) {
            console.error("Erreur lors de la récupération des données :", error);
        }
        this.state.isLoading = false;

        // Render charts after loading data
        this.renderCharts();
    }

    async onRefresh() {
        await this.fetchDashboardData();
    }

    async onBranchChange(ev) {
        this.state.selectedBranchId = ev.target.value;
        await this.fetchDashboardData();
    }

    renderCharts() {
        // Destroy existing chart instances
        if (this.revenueChart) {
            this.revenueChart.destroy();
        }
        if (this.studentChart) {
            this.studentChart.destroy();
        }

        // 1. REVENUE MONTHLY BAR CHART
        const revenueEl = this.revenueChartRef.el;
        if (revenueEl) {
            this.revenueChart = new window.Chart(revenueEl, {
                type: 'bar',
                data: {
                    labels: this.state.chartData.revenue.labels,
                    datasets: [{
                        label: 'Revenus Mensuels (DA)',
                        data: this.state.chartData.revenue.values,
                        backgroundColor: 'rgba(26, 71, 137, 0.85)',
                        borderColor: '#1A4789',
                        borderWidth: 1.5,
                        borderRadius: 8,
                        hoverBackgroundColor: 'rgba(230, 9, 125, 0.85)',
                        hoverBorderColor: '#E6097D',
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: '#0F172A',
                            titleFont: { family: 'Cairo' },
                            bodyFont: { family: 'Cairo' },
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: '#E2E8F0' },
                            ticks: { font: { family: 'Cairo' } }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { font: { family: 'Cairo' } }
                        }
                    }
                }
            });
        }

        // 2. STUDENT STATUS DONUT CHART
        const studentEl = this.studentChartRef.el;
        if (studentEl) {
            this.studentChart = new window.Chart(studentEl, {
                type: 'doughnut',
                data: {
                    labels: ['Actifs', 'Alerte (≤2 séanc.)', 'Expirés'],
                    datasets: [{
                        data: [this.state.totalActive, this.state.totalAlert, this.state.totalExpired],
                        backgroundColor: [
                            'rgba(16, 185, 129, 0.85)', // Success Green
                            'rgba(245, 158, 11, 0.85)', // Warning Orange
                            'rgba(239, 68, 68, 0.85)'   // Danger Red
                        ],
                        borderColor: '#FFFFFF',
                        borderWidth: 2,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                font: { family: 'Cairo', size: 11 },
                                boxWidth: 12
                            }
                        },
                        tooltip: {
                            backgroundColor: '#0F172A',
                            bodyFont: { family: 'Cairo' },
                        }
                    },
                    cutout: '65%'
                }
            });
        }
    }

    // ------------------------------------------
    // DYNAMIC NAV ACTIONS
    // ------------------------------------------
    openStudents(statusFilter) {
        const baseDomain = [];
        if (this.state.selectedBranchId !== "all") {
            baseDomain.push(["branch_id", "=", parseInt(this.state.selectedBranchId)]);
        }

        let domain = [...baseDomain];
        let title = "Tous les Étudiants";

        if (statusFilter === "active") {
            domain.push(["status", "=", "active"]);
            title = "Étudiants Actifs";
        } else if (statusFilter === "alert") {
            domain.push(["sessions_remaining", "<=", 2], ["sessions_remaining", ">", 0]);
            title = "Étudiants en Alerte";
        } else if (statusFilter === "expired") {
            domain.push(["status", "=", "expired"]);
            title = "Étudiants Expirés";
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            name: title,
            res_model: "winners.student",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            target: "current",
        });
    }

    openPayments() {
        const baseDomain = [];
        if (this.state.selectedBranchId !== "all") {
            baseDomain.push(["branch_id", "=", parseInt(this.state.selectedBranchId)]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Gestion des Paiements (Bons)",
            res_model: "winners.payment",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            domain: baseDomain,
            target: "current",
        });
    }

    openTeachers() {
        const baseDomain = [];
        if (this.state.selectedBranchId !== "all") {
            baseDomain.push(["branch_id", "=", parseInt(this.state.selectedBranchId)]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Enseignants",
            res_model: "winners.teacher",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            domain: baseDomain,
            target: "current",
        });
    }

    openSessions() {
        const baseDomain = [];
        if (this.state.selectedBranchId !== "all") {
            baseDomain.push(["branch_id", "=", parseInt(this.state.selectedBranchId)]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Séances du Jour",
            res_model: "winners.session",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            domain: baseDomain,
            target: "current",
        });
    }

    openRooms() {
        const baseDomain = [];
        if (this.state.selectedBranchId !== "all") {
            baseDomain.push(["branch_id", "=", parseInt(this.state.selectedBranchId)]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Salles de Classe",
            res_model: "winners.room",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            domain: baseDomain,
            target: "current",
        });
    }

    openPaymentRecord(paymentId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "winners.payment",
            res_id: paymentId,
            views: [[false, "form"]],
            target: "current"
        });
    }

    openSessionRecord(sessionId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "winners.session",
            res_id: sessionId,
            views: [[false, "form"]],
            target: "current"
        });
    }

    formatCurrency(value) {
        return new Intl.NumberFormat("fr-DZ", {
            style: 'currency',
            currency: 'DZD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(value).replace('DZD', 'DA');
    }

    formatTime(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        // Correct time offset if needed, format hh:mm
        return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    }
}

registry
    .category("actions")
    .add("winners_dashboard", WinnersDashboard);
