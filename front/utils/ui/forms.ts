export function getYearOptions(startYear: number = 2025, labelAll: string = "Toutes") {
  const currentYear = new Date().getFullYear();
  const years = [];
  for (let year = startYear; year <= currentYear; year++) {
    years.push(year.toString());
  }
  return [
    { value: "", label: labelAll },
    ...years.map((year) => ({
      value: year,
      label: year,
    })),
  ];
}
