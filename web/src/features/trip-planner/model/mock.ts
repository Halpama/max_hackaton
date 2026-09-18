import type { InterestId, RoutePlan, TripDraft, TripPace } from './types'

export const INTEREST_OPTIONS: Array<{ id: InterestId; label: string }> = [
  { id: 'sights', label: 'Достопримечательности' },
  { id: 'museums', label: 'Музеи' },
  { id: 'gastro', label: 'Гастрономия' },
  { id: 'walks', label: 'Прогулки' },
  { id: 'nature', label: 'Природа' },
  { id: 'unusual', label: 'Необычные места' },
]

export const PACE_OPTIONS: Array<{ id: TripPace; label: string }> = [
  { id: 'calm', label: 'Спокойный' },
  { id: 'medium', label: 'Средний' },
  { id: 'active', label: 'Активный' },
]

export const LOADING_STEPS = [
  'Анализ предпочтений',
  'Подбор мест',
  'Расчёт времени в пути',
  'Распределение бюджета',
  'Формирование расписания',
] as const

export const DEFAULT_TRIP_DRAFT: TripDraft = {
  destination: 'Санкт-Петербург',
  startDate: '2026-09-15',
  endDate: '2026-09-17',
  budget: 45000,
  travelers: 2,
  interests: ['sights', 'museums', 'gastro'],
  pace: 'medium',
  findHousing: false,
}

export const MOCK_ROUTE: RoutePlan = {
  city: 'Санкт-Петербург',
  dateLabel: '15–17 сентября',
  travelersLabel: '2 путешественника',
  budgetLabel: '~45 000 ₽',
  places: {
    hermitage: {
      id: 'hermitage',
      title: 'Эрмитаж',
      category: 'Музей изобразительного и декоративно-прикладного искусства',
      categoryKind: 'museum',
      priceLabel: '800 ₽',
      priceValue: 800,
      durationLabel: '2 часа',
      timeRange: '09:00 – 11:00',
      rating: 4.9,
      reviewsLabel: '12k отзывов',
      address: 'Дворцовая пл., 2',
      description:
        'Один из крупнейших и наиболее значимых художественных и культурно-исторических музеев в мире. Посещение обязательно начинается с парадных залов Зимнего дворца.',
      imageUrl:
        'https://images.unsplash.com/photo-1576422498609-459417ced4b8?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080',
    },
    palaceSquare: {
      id: 'palaceSquare',
      title: 'Дворцовая площадь',
      category: 'Локация',
      categoryKind: 'location',
      priceLabel: 'Бесплатно',
      durationLabel: '45 мин',
      timeRange: '11:30 – 12:15',
      rating: 4.8,
      reviewsLabel: '8k отзывов',
      address: 'Дворцовая площадь',
      description:
        'Главная площадь Петербурга и сердце имперского города. Отсюда удобно начать прогулку к Неве и Адмиралтейству.',
      imageUrl:
        'https://images.unsplash.com/photo-1556610961-2fecc5937175?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080',
    },
    pyshechnaya: {
      id: 'pyshechnaya',
      title: 'Легендарная Пышечная',
      category: 'Гастрономия',
      categoryKind: 'food',
      priceLabel: '~500 ₽',
      priceValue: 500,
      durationLabel: '1 час',
      timeRange: '13:00 – 14:00',
      rating: 4.6,
      reviewsLabel: '3k отзывов',
      address: 'Большая Конюшенная ул., 25',
      description:
        'Классическая петербургская пышечная с горячими пончиками и кофе. Короткая, но обязательная гастро-остановка.',
      imageUrl:
        'https://images.unsplash.com/photo-1551024601-bec78aea704b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080',
    },
  },
  days: [
    {
      id: 'day-1',
      label: 'День 1',
      activities: [
        {
          id: 'a1',
          placeId: 'hermitage',
          time: '09:00',
          durationLabel: '2 часа',
          title: 'Государственный Эрмитаж',
          meta: 'Музей • 500 ₽',
        },
        {
          id: 'a2',
          placeId: 'palaceSquare',
          time: '11:30',
          durationLabel: '45 мин',
          title: 'Дворцовая площадь',
          meta: 'Локация • Бесплатно',
        },
        {
          id: 'a3',
          placeId: 'pyshechnaya',
          time: '13:00',
          durationLabel: '1 час',
          title: 'Легендарная Пышечная',
          meta: 'Гастрономия • ~500 ₽',
        },
      ],
      transits: [
        { mode: 'walk', label: 'Пешком 10 мин (Дворцовая площадь)' },
        { mode: 'taxi', label: 'Такси 5 мин' },
      ],
    },
    {
      id: 'day-2',
      label: 'День 2',
      activities: [
        {
          id: 'b1',
          placeId: 'palaceSquare',
          time: '10:00',
          durationLabel: '1.5 часа',
          title: 'Прогулка по центру',
          meta: 'Прогулки • Бесплатно',
        },
        {
          id: 'b2',
          placeId: 'pyshechnaya',
          time: '12:00',
          durationLabel: '2 часа',
          title: 'Гастро-маршрут',
          meta: 'Гастрономия • ~2 000 ₽',
        },
      ],
      transits: [{ mode: 'walk', label: 'Пешком 15 мин' }],
    },
    {
      id: 'day-3',
      label: 'День 3',
      activities: [
        {
          id: 'c1',
          placeId: 'hermitage',
          time: '11:00',
          durationLabel: '3 часа',
          title: 'Свободный день в музее',
          meta: 'Музей • 800 ₽',
        },
      ],
      transits: [],
    },
  ],
}
