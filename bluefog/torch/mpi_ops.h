#ifndef BLUEFOG_TORCH_MPI_OPS_H
#define BLUEFOG_TORCH_MPI_OPS_H

#include "../common/common.h"
#include <TH/TH.h>

#if HAVE_CUDA
#include <THC/THC.h>
#endif

namespace bluefog {
namespace torch {

#define ALLREDUCE_H(torch_Tensor, THTensor)                                    \
  extern "C" int bluefog_torch_allreduce_async_##torch_Tensor(                 \
      THTensor* tensor, THTensor* output, int average, char* name);

ALLREDUCE_H(torch_IntTensor, THIntTensor)
ALLREDUCE_H(torch_LongTensor, THLongTensor)
ALLREDUCE_H(torch_FloatTensor, THFloatTensor)
ALLREDUCE_H(torch_DoubleTensor, THDoubleTensor)

#if HAVE_CUDA
ALLREDUCE_H(torch_cuda_IntTensor, THCudaIntTensor)
ALLREDUCE_H(torch_cuda_LongTensor, THCudaLongTensor)
ALLREDUCE_H(torch_cuda_FloatTensor, THCudaTensor)
ALLREDUCE_H(torch_cuda_DoubleTensor, THCudaDoubleTensor)
#endif

#define BROADCAST_H(torch_Tensor, THTensor)                                    \
  extern "C" int bluefog_torch_broadcast_async_##torch_Tensor(                 \
      THTensor* tensor, THTensor* output, int root_rank, char* name);

BROADCAST_H(torch_IntTensor, THIntTensor)
BROADCAST_H(torch_LongTensor, THLongTensor)
BROADCAST_H(torch_FloatTensor, THFloatTensor)
BROADCAST_H(torch_DoubleTensor, THDoubleTensor)

#if HAVE_CUDA
BROADCAST_H(torch_cuda_IntTensor, THCudaIntTensor)
BROADCAST_H(torch_cuda_LongTensor, THCudaLongTensor)
BROADCAST_H(torch_cuda_FloatTensor, THCudaTensor)
BROADCAST_H(torch_cuda_DoubleTensor, THCudaDoubleTensor)
#endif

#define ALLGATHER_H(torch_Tensor, THTensor)                                    \
  extern "C" int bluefog_torch_allgather_async_##torch_Tensor(                 \
      THTensor* tensor, THTensor* output, char* name);

ALLGATHER_H(torch_IntTensor, THIntTensor)
ALLGATHER_H(torch_LongTensor, THLongTensor)
ALLGATHER_H(torch_FloatTensor, THFloatTensor)
ALLGATHER_H(torch_DoubleTensor, THDoubleTensor)

#if HAVE_CUDA
ALLGATHER_H(torch_cuda_IntTensor, THCudaIntTensor)
ALLGATHER_H(torch_cuda_LongTensor, THCudaLongTensor)
ALLGATHER_H(torch_cuda_FloatTensor, THCudaTensor)
ALLGATHER_H(torch_cuda_DoubleTensor, THCudaDoubleTensor)
#endif

#define NEIGHBOR_ALLGATHER_H(torch_Tensor, THTensor)                           \
  extern "C" int bluefog_torch_neighbor_allgather_async_##torch_Tensor(        \
      THTensor* tensor, THTensor* output, char* name);

NEIGHBOR_ALLGATHER_H(torch_IntTensor, THIntTensor)
NEIGHBOR_ALLGATHER_H(torch_LongTensor, THLongTensor)
NEIGHBOR_ALLGATHER_H(torch_FloatTensor, THFloatTensor)
NEIGHBOR_ALLGATHER_H(torch_DoubleTensor, THDoubleTensor)

#if HAVE_CUDA
NEIGHBOR_ALLGATHER_H(torch_cuda_IntTensor, THCudaIntTensor)
NEIGHBOR_ALLGATHER_H(torch_cuda_LongTensor, THCudaLongTensor)
NEIGHBOR_ALLGATHER_H(torch_cuda_FloatTensor, THCudaTensor)
NEIGHBOR_ALLGATHER_H(torch_cuda_DoubleTensor, THCudaDoubleTensor)
#endif

#define NEIGHBOR_ALLREDUCE_H(torch_Tensor, THTensor)                           \
  extern "C" int bluefog_torch_neighbor_allreduce_async_##torch_Tensor(        \
      THTensor* tensor, THTensor* output, int average, char* name);

NEIGHBOR_ALLREDUCE_H(torch_IntTensor, THIntTensor)
NEIGHBOR_ALLREDUCE_H(torch_LongTensor, THLongTensor)
NEIGHBOR_ALLREDUCE_H(torch_FloatTensor, THFloatTensor)
NEIGHBOR_ALLREDUCE_H(torch_DoubleTensor, THDoubleTensor)

#if HAVE_CUDA
NEIGHBOR_ALLREDUCE_H(torch_cuda_IntTensor, THCudaIntTensor)
NEIGHBOR_ALLREDUCE_H(torch_cuda_LongTensor, THCudaLongTensor)
NEIGHBOR_ALLREDUCE_H(torch_cuda_FloatTensor, THCudaTensor)
NEIGHBOR_ALLREDUCE_H(torch_cuda_DoubleTensor, THCudaDoubleTensor)
#endif

extern "C" int bluefog_torch_poll(int handle);
extern "C" void bluefog_torch_wait_and_clear(int handle);

}  // namespace torch
}  // namespace bluefog

#endif  // BLUEFOG_TORCH_MPI_OPS_H