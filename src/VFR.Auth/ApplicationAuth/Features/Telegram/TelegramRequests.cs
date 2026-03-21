using MediatR;
using System.Collections.Generic;

namespace ApplicationAuth.Features.Telegram;

public record TestInsertMinimalCommand(string Text) : IRequest<TelegramMessageResponse>;

public record SaveMessageMinimalCommand(TelegramMessageRequest Model) : IRequest<TelegramMessageResponse>;

public record GetMessagesMinimalQuery(string UserToken) : IRequest<IEnumerable<TelegramMessageResponse>>;
