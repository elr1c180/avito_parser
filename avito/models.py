from typing import Any, Dict, List, Optional

from pydantic import BaseModel, HttpUrl, RootModel


class Category(BaseModel):
    id: int
    name: str
    slug: str
    rootId: int
    compare: bool
    pageRootId: Optional[int] = None


class Location(BaseModel):
    id: int
    name: str
    namePrepositional: str
    isCurrent: bool
    isRegion: bool


class AddressDetailed(BaseModel):
    locationName: str


class PriceDetailed(BaseModel):
    enabled: bool
    fullString: str
    hasValue: bool
    postfix: str
    string: str
    stringWithoutDiscount: Optional[str] = None
    title: Dict[str, str]
    titleDative: str
    value: int
    wasLowered: bool
    exponent: str


class Image(RootModel):
    root: Dict[str, HttpUrl]


class Geo(BaseModel):
    geoReferences: List[Any]
    formattedAddress: str


class Contacts(BaseModel):
    phone: bool
    delivery: bool
    message: bool
    messageTitle: str
    action: str
    onModeration: bool
    hasCVPackage: bool
    hasEmployeeBalanceForCv: bool
    serviceBooking: bool


class Gallery(BaseModel):
    alt: Optional[str] = None
    cropImagesInfo: Optional[Any] = None
    extraPhoto: Optional[Any] = None
    hasLeadgenOverlay: bool
    has_big_image: bool
    imageAlt: str
    imageLargeUrl: str
    imageLargeVipUrl: str
    imageUrl: str
    imageVipUrl: str
    image_large_urls: List[Any]
    image_urls: List[Any]
    images: List[Any]
    imagesCount: int
    isFirstImageHighImportance: bool
    isLazy: bool
    noPhoto: bool
    showSlider: bool
    wideSnippetUrls: List[Any]


class UserLogo(BaseModel):
    link: Optional[str] = None
    src: Optional[Any] = None
    developerId: Optional[int] = None


class IvaComponent(BaseModel):
    component: str
    payload: Optional[Dict[str, Any]] = None


class IvaStep(BaseModel):
    componentData: IvaComponent
    payload: Optional[Dict[str, Any]] = None
    default: bool


class Item(BaseModel):
    id: Optional[Any] = None
    categoryId: Optional[Any] = None
    locationId: Optional[Any] = None
    isVerifiedItem: Optional[bool] = None
    urlPath: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[Category] = None
    location: Optional[Location] = None
    addressDetailed: Optional[AddressDetailed] = None
    sortTimeStamp: Optional[int] = None
    turnOffDate: Optional[Any] = None
    priceDetailed: Optional[PriceDetailed] = None
    normalizedPrice: Optional[str] = None
    priceWithoutDiscount: Optional[str] = None
    discountPercent: Optional[Any] = None
    lastMinuteOffer: Optional[Any] = None
    images: Optional[List[Image]] = None
    imagesCount: Optional[int] = None
    isFavorite: Optional[bool] = None
    isNew: Optional[bool] = None
    geo: Optional[Geo] = None
    phoneImage: Optional[str] = None
    cvViewed: Optional[bool] = None
    isXl: Optional[bool] = None
    hasFooter: Optional[bool] = None
    contacts: Optional[Contacts] = None
    gallery: Optional[Gallery] = None
    loginLink: Optional[str] = None
    authLink: Optional[str] = None
    userLogo: Optional[UserLogo] = None
    isMarketplace: Optional[bool] = None
    iva: Optional[Dict[str, List[IvaStep]]] = None
    hasVideo: Optional[bool] = None
    hasRealtyLayout: Optional[bool] = None
    coords: Optional[Dict[str, Any]] = None
    groupData: Optional[Any] = None
    isReMapPromotion: Optional[bool] = None
    isReserved: Optional[bool] = None
    type: Optional[str] = None
    ratingExperimentGroup: Optional[str] = None
    isRatingExperiment: Optional[bool] = None
    closedItemsText: Optional[str] = None
    closestAddressId: Optional[int] = None
    isSparePartsCompatibility: Optional[bool] = None
    sellerId: Optional[str] = None
    isPromotion: bool = False
    total_views: Optional[int] = None
    today_views: Optional[int] = None


class ItemsResponse(BaseModel):
    items: List[Item]
