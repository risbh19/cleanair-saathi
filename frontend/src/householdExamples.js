const commute = (mode, distance_km, depart_time, return_time) => ({
  mode, distance_km, depart_time, return_time,
});

export const householdExamples = [
  {
    en: "Family with a toddler and grandparent",
    hi: "छोटे बच्चे और बुज़ुर्ग वाला परिवार",
    fields: {
      home_type: "flat", cooking_fuel: "lpg", budget_band: "medium",
      room_area_m2: 16, ceiling_m: 2.8, windows_leaky: false, purifier_cadr_m3h: 200,
      members: [
        { age_band: "adult", sensitive: false, commutes: [commute("car", 4, "08:00", "14:00")] },
        { age_band: "child", sensitive: true, commutes: [] },
        { age_band: "older_adult", sensitive: true, commutes: [] },
      ],
    },
  },
  {
    en: "Two adults with scooter commutes",
    hi: "स्कूटर से काम पर जाने वाले दो वयस्क",
    fields: {
      home_type: "flat", cooking_fuel: "lpg", budget_band: "low",
      room_area_m2: 12, ceiling_m: 2.7, windows_leaky: false, purifier_cadr_m3h: 0,
      members: [
        { age_band: "adult", sensitive: false, commutes: [commute("two_wheeler", 14, "08:30", "18:30")] },
        { age_band: "adult", sensitive: false, commutes: [commute("two_wheeler", 10, "09:00", "18:00")] },
      ],
    },
  },
  {
    en: "Family with two schoolchildren",
    hi: "दो स्कूली बच्चों वाला परिवार",
    fields: {
      home_type: "independent_house", cooking_fuel: "png", budget_band: "medium",
      room_area_m2: 20, ceiling_m: 3, windows_leaky: true, purifier_cadr_m3h: 0,
      members: [
        { age_band: "adult", sensitive: false, commutes: [] },
        { age_band: "adult", sensitive: false, commutes: [] },
        { age_band: "child", sensitive: false, commutes: [commute("bus", 5, "07:30", "14:30")] },
        { age_band: "child", sensitive: false, commutes: [commute("bus", 5, "07:30", "14:30")] },
      ],
    },
  },
];
