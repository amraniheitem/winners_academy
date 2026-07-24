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
            canSeeTeacherEarnings: false,
            branches: [],
            selectedBranchId: "all",
            currentLang: "fr_FR",
            isArabic: false,

            // 1. Students KPIs
            totalStudents: 0,
            totalActive: 0,
            totalAlert: 0,
            totalExpired: 0,
            newStudentsMonth: 0,

            // 2. Financial KPIs
            revenueWeek: 0,
            revenueMonth: 0,
            revenueYear: 0,
            avgPaymentAmount: 0,
            totalConfirmedPayments: 0,
            teacherEarningsMonth: 0,
            companyEarningsMonth: 0,

            // 3. Teachers & Classes KPIs
            totalTeachers: 0,
            totalGroups: 0,

            // 4. Rooms & Schedules KPIs
            totalRooms: 0,
            sessionsToday: 0,
            scheduleTodayCount: 0,
            currentDayName: "",
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
            this.state.currentLang = this.user.lang || "fr_FR";
            this.state.isArabic = this.state.currentLang.startsWith("ar");
            this.state.isSuperAdmin = await this.user.hasGroup(
                "winners_auth.winners_group_super_admin"
            );
            this.state.canSeeTeacherEarnings = (
                this.state.isSuperAdmin
                || await this.user.hasGroup("winners_auth.winners_group_director")
                || await this.user.hasGroup("winners_auth.winners_group_secretary")
                || await this.user.hasGroup("winners_auth.winners_group_teacher")
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

    formatTimeRange(start, end) {
        if (!start && start !== 0) return "-";
        const formatFloat = f => {
            const hrs = Math.floor(f);
            const mins = Math.round((f - hrs) * 60);
            return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
        };
        return `${formatFloat(start)} - ${formatFloat(end)}`;
    }

    async onLangChange(ev) {
        const newLang = ev.target.value;
        if (newLang === this.state.currentLang) return;
        this.state.isLoading = true;
        try {
            await this.orm.call("res.users", "set_user_language", [newLang]);
            window.location.reload();
        } catch (e) {
            console.error("Erreur changement de langue:", e);
            this.state.isLoading = false;
        }
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
            // 2. FINANCIAL METRICS (WEEK, MONTH, YEAR)
            // ------------------------------------------
            const weekDay = (now.getDay() + 6) % 7; // Monday = 0
            const weekStart = new Date(now);
            weekStart.setDate(now.getDate() - weekDay);
            weekStart.setHours(0, 0, 0, 0);

            const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
            const yearStart = new Date(now.getFullYear(), 0, 1);

            const confirmedPayments = await this.orm.searchRead(
                "winners.payment",
                [...baseDomain, ["state", "=", "confirmed"]],
                ["id", "student_id", "amount", "date", "state"],
                { order: "date desc, id desc" }
            );

            this.state.totalConfirmedPayments = confirmedPayments.length;
            const totalRevenue = confirmedPayments.reduce((acc, p) => acc + (p.amount || 0), 0);

            let sumWeek = 0, sumMonth = 0, sumYear = 0;
            confirmedPayments.forEach(p => {
                if (p.date) {
                    const pDate = new Date(p.date);
                    if (pDate >= weekStart) sumWeek += (p.amount || 0);
                    if (pDate >= monthStart) sumMonth += (p.amount || 0);
                    if (pDate >= yearStart) sumYear += (p.amount || 0);
                }
            });

            this.state.revenueWeek = sumWeek;
            this.state.revenueMonth = sumMonth > 0 ? sumMonth : totalRevenue;
            this.state.revenueYear = sumYear > 0 ? sumYear : totalRevenue;
            this.state.avgPaymentAmount = confirmedPayments.length > 0 ? (totalRevenue / confirmedPayments.length) : 0;

            if (this.state.canSeeTeacherEarnings) {
                const teacherSheets = await this.orm.searchRead(
                    "winners.teacher.earning.sheet",
                    baseDomain,
                    ["teacher_amount", "company_amount"]
                );
                this.state.teacherEarningsMonth = teacherSheets.reduce((acc, s) => acc + (s.teacher_amount || 0), 0);
                this.state.companyEarningsMonth = teacherSheets.reduce((acc, s) => acc + (s.company_amount || 0), 0);
            }

            // ------------------------------------------
            // 3. TEACHERS & GROUPS
            // ------------------------------------------
            this.state.totalTeachers = await this.orm.searchCount("winners.teacher", baseDomain);
            this.state.totalGroups = await this.orm.searchCount("winners.group", baseDomain);

            // ------------------------------------------
            // 4. ROOMS & SESSIONS FOR TODAY
            // ------------------------------------------
            this.state.totalRooms = await this.orm.searchCount("winners.room", baseDomain);

            const daysEng = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
            const daysAr = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'];
            const daysFr = ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'];
            const dayIndex = now.getDay();
            const currentDayEng = daysEng[dayIndex];
            this.state.currentDayName = this.state.isArabic ? daysAr[dayIndex] : daysFr[dayIndex];

            const todayStr = now.toISOString().split("T")[0];
            const sessionsForTodayCount = await this.orm.searchCount(
                "winners.session",
                [...baseDomain, ["date", ">=", todayStr + " 00:00:00"], ["date", "<=", todayStr + " 23:59:59"]]
            );

            this.state.scheduleTodayCount = await this.orm.searchCount(
                "winners.schedule",
                [...baseDomain, ["day_of_week", "=", currentDayEng]]
            );

            this.state.sessionsToday = sessionsForTodayCount > 0 ? sessionsForTodayCount : this.state.scheduleTodayCount;

            this.state.attendanceToday = await this.orm.searchCount(
                "winners.attendance.line",
                [...baseDomain, ["status", "in", ["present", "late"]]]
            );

            // ------------------------------------------
            // 5. RECENT LISTS (5 CONFIRMED PAYMENTS & TODAY TIMETABLE)
            // ------------------------------------------
            this.state.recentPayments = confirmedPayments.slice(0, 5);

            const timetableEntries = await this.orm.searchRead(
                "winners.schedule",
                [...baseDomain, ["day_of_week", "=", currentDayEng]],
                ["id", "group_id", "teacher_id", "room_id", "time_start", "time_end"],
                { limit: 10, order: "time_start asc" }
            );

            this.state.todaySessions = timetableEntries.map(s => ({
                id: s.id,
                group_name: s.group_id ? s.group_id[1] : '-',
                teacher_name: s.teacher_id ? s.teacher_id[1] : '-',
                room_name: s.room_id ? s.room_id[1] : '-',
                time_range: this.formatTimeRange(s.time_start, s.time_end),
            }));

            // ------------------------------------------
            // 6. CHART DATA (LAST 6 MONTHS REVENUE)
            // ------------------------------------------
            const months = this.state.isArabic
                ? ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان", "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
                : ["Janv", "Févr", "Mars", "Avril", "Mai", "Juin", "Juil", "Août", "Sept", "Oct", "Nov", "Déc"];
            
            const revenueByMonth = {};
            for (let i = 5; i >= 0; i--) {
                const d = new Date();
                d.setMonth(d.getMonth() - i);
                const mLabel = months[d.getMonth()] + " " + d.getFullYear().toString().substr(-2);
                revenueByMonth[mLabel] = 0;
            }

            confirmedPayments.forEach(p => {
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
            const chartLabel = this.state.isArabic ? 'المداخيل الشهرية (د.ج)' : 'Revenus Mensuels (DA)';
            this.revenueChart = new window.Chart(revenueEl, {
                type: 'bar',
                data: {
                    labels: this.state.chartData.revenue.labels,
                    datasets: [{
                        label: chartLabel,
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
            const donutLabels = this.state.isArabic
                ? ['نشطون', 'تنبيه (≤2 حصص)', 'منتهون']
                : ['Actifs', 'Alerte (≤2 séanc.)', 'Expirés'];

            this.studentChart = new window.Chart(studentEl, {
                type: 'doughnut',
                data: {
                    labels: donutLabels,
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
        if (this.state.isArabic) {
            return new Intl.NumberFormat("ar-DZ", {
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            }).format(value) + " د.ج";
        }
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
