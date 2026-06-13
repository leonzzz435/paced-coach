const GRID_COL_START_BY_UTC_WEEKDAY = [
    "sm:col-start-7",
    "sm:col-start-1",
    "sm:col-start-2",
    "sm:col-start-3",
    "sm:col-start-4",
    "sm:col-start-5",
    "sm:col-start-6",
] as const;

type PlanCalendarDay = {
    date: string;
};

function parseUtcDate(dateStr: string): Date | null {
    if (!dateStr) return null;
    const date = new Date(`${dateStr}T00:00:00Z`);
    return Number.isNaN(date.getTime()) ? null : date;
}

function formatMonthYear(date: Date): string {
    return date.toLocaleDateString("en-US", { month: "long", year: "numeric", timeZone: "UTC" });
}

function formatMonthDayYear(date: Date): string {
    return date.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric", timeZone: "UTC" });
}

function formatMonthRange(startDate: Date, endDate: Date): string {
    const startMonth = startDate.toLocaleDateString("en-US", { month: "long", timeZone: "UTC" });
    const startDay = startDate.getUTCDate();
    const endDay = endDate.getUTCDate();
    const year = endDate.getUTCFullYear();

    if (startDate.getTime() === endDate.getTime()) {
        return formatMonthDayYear(startDate);
    }

    return `${startMonth} ${startDay}-${endDay}, ${year}`;
}

export function formatPlanDayNumber(dateStr: string): string {
    const date = parseUtcDate(dateStr);
    if (!date) return "";
    return date.toLocaleDateString("en-US", { day: "numeric", timeZone: "UTC" });
}

export function getMonthGridColumnStartClass(dateStr: string): string {
    const date = parseUtcDate(dateStr);
    if (!date) return "";
    return GRID_COL_START_BY_UTC_WEEKDAY[date.getUTCDay()];
}

export function formatPlanRangeLabel(monthKey: string, days: PlanCalendarDay[]): string {
    const monthStart = parseUtcDate(`${monthKey}-01`);
    if (!monthStart || days.length === 0) return monthKey;

    const sortedDays = days
        .filter((day) => day.date?.startsWith(`${monthKey}-`))
        .slice()
        .sort((left, right) => left.date.localeCompare(right.date));

    if (sortedDays.length === 0) return formatMonthYear(monthStart);

    const firstDate = parseUtcDate(sortedDays[0].date);
    const lastDate = parseUtcDate(sortedDays[sortedDays.length - 1].date);
    if (!firstDate || !lastDate) return formatMonthYear(monthStart);

    const monthEnd = new Date(Date.UTC(monthStart.getUTCFullYear(), monthStart.getUTCMonth() + 1, 0));
    const coversWholeMonth = firstDate.getUTCDate() === 1 && lastDate.getUTCDate() === monthEnd.getUTCDate();

    return coversWholeMonth ? formatMonthYear(monthStart) : formatMonthRange(firstDate, lastDate);
}
