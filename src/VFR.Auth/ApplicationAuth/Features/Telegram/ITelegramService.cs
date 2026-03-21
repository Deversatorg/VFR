using System.Collections.Generic;
using System.Threading.Tasks;

namespace ApplicationAuth.Features.Telegram
{
    public interface ITelegramService
    {
        public Task<TelegramMessageResponse> TestInsert(string text);

        public Task<TelegramMessageResponse> SaveMessage(TelegramMessageRequest model);

        public Task<IEnumerable<TelegramMessageResponse>> GetMessagesByUserToken(string userToken);

        public Task<IEnumerable<TelegramStickerResponse>> GetTopStickers();

        public Task<TelegramStickerResponse> SaveStickerRate(string fileUniqueId, string stickerId);

    }
}
